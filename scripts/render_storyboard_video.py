#!/usr/bin/env python3
"""Bounded local draft MP4 export from governed storyboards; no network access."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts.production import StoryboardPayload
from services.api.src.main import get_store

VERSION = "local-scene-export-1"
FPS = 24
PALETTES = [("#F2E6D0", "#28251D", "#BD4D2D"), ("#DFE8D7", "#24342C", "#4E7860"), ("#F6D5BA", "#38271F", "#B94D2E")]
RETIRED = {"rejected", "archived", "deprecated"}


def wrapped(text, font, width):
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        if font.getlength(word) > width:
            raise ValueError("Unbreakable text exceeds the export width; prepare readable wording.")
        candidate = (current + " " + word).strip()
        if current and font.getlength(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def font(size, title=False):
    candidates = [
        "/System/Library/Fonts/Avenir Next Condensed.ttc" if title else "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def text_block(draw, text, box, color, size=24, minimum=15, title=False):
    x, y, width, height = box
    for point_size in range(size, minimum - 1, -1):
        face = font(point_size, title)
        lines = wrapped(text, face, width)
        spacing = round(point_size * 1.28)
        if len(lines) * spacing <= height:
            for line in lines:
                draw.text((x, y), line, font=face, fill=color, stroke_width=0)
                y += spacing
            return
    raise ValueError("Text does not fit the export canvas without becoming too small.")


def plates(scene, index, total, aspect):
    portrait = aspect == "9:16"
    width, height = (432, 768) if portrait else (768, 432)
    background, ink, accent = PALETTES[index % len(PALETTES)]
    base = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(base)
    for y in range(0, height, 36):
        draw.line((0, y, width, y), fill="#D7CCB7", width=1)
    circle = (width * .56, -height * .14, width * 1.24, height * .68)
    draw.ellipse(circle, outline=accent, width=14)
    draw.ellipse((width * .7, height * .65, width * 1.13, height * 1.2), outline="#D6C4A9", width=30)
    draw.text((24, 14), "SMARTGLASSES / PRIVATE DRAFT", font=font(11), fill=ink)
    draw.text((24, height - 40), "ABSTRACT ARTWORK / NOT PRODUCT PHOTOGRAPHY", font=font(9), fill=ink)
    draw.text((24, height - 25), "NOT HANDS-ON TESTED / SOURCE NOTES IN REVIEW PACKET", font=font(9), fill=ink)
    counter = f"{index + 1:02d} / {total:02d}"
    draw.text((width - 75, 14), counter, font=font(11), fill=ink)

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    copy = ImageDraw.Draw(layer)
    copy.text((26, 52), scene.primitive.replace("_", " ").upper(), font=font(11), fill=accent)
    text_block(copy, scene.heading, (24, 76, width - 48, 100 if portrait else 80),
               ink, size=36 if portrait else 38, minimum=24, title=True)
    top = 196 if portrait else 172
    bottom = height - (150 if portrait else 104)
    area_height = bottom - top
    gap = 12
    count = len(scene.lines)
    paired = scene.primitive == "comparison_table" and count == 2 and not portrait
    for number, line in enumerate(scene.lines):
        if paired:
            card_width = (width - 48 - gap) // 2
            box = (24 + number * (card_width + gap), top, card_width, area_height)
        else:
            card_height = (area_height - gap * max(count - 1, 0)) // max(count, 1)
            box = (24, top + number * (card_height + gap), width - 48, card_height)
        x, y, card_width, card_height = box
        copy.rounded_rectangle((x, y, x + card_width, y + card_height), radius=12, fill="#FFFFFFDE")
        text_block(copy, line, (x + 14, y + 9, card_width - 28, card_height - 16),
                   ink, size=24 if portrait else 23, minimum=16)
    note = scene.notes[0] if scene.notes else "Editorial framing; no new factual claim."
    text_block(copy, note, (26, height - (132 if portrait else 92), width - 52, 70 if portrait else 44),
               ink, size=12, minimum=10)
    return base, layer


def animated_frame(base, layer, seconds, duration):
    frame = base.copy()
    progress = min(max(seconds / .55, 0), 1)
    eased = 1 - (1 - progress) ** 3
    shift = round((1 - eased) * 26)
    frame.paste(layer, (0, shift), layer)
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, frame.height - 4, round(frame.width * min(seconds / duration, 1)), frame.height), fill="#B94D2E")
    return frame


def current_bundle(store, object_id):
    storyboard = store.get(object_id)
    if storyboard.object_type != "storyboard" or storyboard.status.value in RETIRED:
        raise ValueError("Choose a non-retired storyboard.")
    plan = StoryboardPayload.model_validate(storyboard.payload)
    brief = store.get(plan.brief_object_id)
    if brief.version != plan.brief_version or brief.status.value in RETIRED:
        raise ValueError("The source brief changed or was retired; rebuild this storyboard.")
    for product_id, version in brief.payload.get("input_versions", {}).items():
        product = store.get(product_id)
        if product.version != version or product.status.value in RETIRED:
            raise ValueError("A source product changed or was retired; rebuild the source brief.")
    claims = {claim["claim_id"]: claim for claim in brief.payload.get("claims", [])}
    for scene in plan.scenes:
        if any(claim_id not in claims for claim_id in scene.claim_ids):
            raise ValueError("The storyboard refers to an unknown claim.")
        if scene.claim_ids and scene.lines != [claims[claim_id]["statement"] for claim_id in scene.claim_ids]:
            raise ValueError("Factual scene wording differs from the linked claim ledger.")
    return storyboard, plan, brief


def export_one(store, object_id, output_root, ffmpeg, max_seconds=180):
    storyboard, plan, brief = current_bundle(store, object_id)
    # Pre-layout every scene before admitting an encoding job.
    scene_plates = [plates(scene, index, len(plan.scenes), plan.aspect_ratio) for index, scene in enumerate(plan.scenes)]
    output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = Path(tempfile.mkdtemp(prefix=plan.workflow_family + "-", dir=output_root))
    destination.chmod(0o700)
    movie = destination / "draft.mp4"
    partial = destination / "draft.partial.mp4"
    width, height = scene_plates[0][0].size
    start = time.monotonic()
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
        "-r", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-threads", "2", "-movflags", "+faststart", "-n", str(partial),
    ]
    with (destination / "encoder.log").open("wb") as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors)
        try:
            for scene, (base, layer) in zip(plan.scenes, scene_plates):
                settled = animated_frame(base, layer, 1, scene.duration_seconds)
                for index in range(scene.duration_seconds * FPS):
                    if time.monotonic() - start > max_seconds:
                        raise TimeoutError("Local render time budget exceeded.")
                    seconds = index / FPS
                    picture = animated_frame(base, layer, seconds, scene.duration_seconds) if seconds < .6 else settled
                    process.stdin.write(picture.tobytes())
            process.stdin.close()
            remaining = max(1, max_seconds - (time.monotonic() - start))
            if process.wait(timeout=remaining) != 0:
                raise RuntimeError("Local encoding failed; inspect the private encoder log.")
        except BaseException:
            process.kill()
            process.wait()
            partial.unlink(missing_ok=True)
            raise
    # Do not silently accept an edit made during rendering.
    latest, _, _ = current_bundle(store, object_id)
    if latest.version != storyboard.version:
        partial.unlink(missing_ok=True)
        raise ValueError("Storyboard changed during export; no final draft was admitted.")
    partial.rename(movie)
    poster_index = next((i for i, scene in enumerate(plan.scenes) if scene.claim_ids), 0)
    base, layer = scene_plates[poster_index]
    animated_frame(base, layer, 1, plan.scenes[poster_index].duration_seconds).save(destination / "poster.png")
    digest = hashlib.sha256(movie.read_bytes()).hexdigest()
    manifest = {
        "renderer_version": VERSION, "created_at": datetime.now(UTC).isoformat(),
        "storyboard_id": storyboard.object_id, "storyboard_version": storyboard.version,
        "brief_id": brief.object_id, "brief_version": brief.version,
        "input_versions": brief.payload.get("input_versions", {}),
        "duration_seconds": plan.duration_seconds, "aspect_ratio": plan.aspect_ratio,
        "width": width, "height": height, "fps": FPS, "mp4_sha256": digest,
        "publication_allowed": False, "approval_status": "not_requested",
        "paid_api_calls": 0, "local_render_seconds": round(time.monotonic() - start, 2),
        "sources": [source.model_dump(mode="json") for source in brief.sources],
        "scene_plan": plan.model_dump(mode="json"),
        "claims": brief.payload.get("claims", []),
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    esc = html.escape
    source_items = "".join(
        f'<li><a href="{esc(source.uri, quote=True)}" rel="noreferrer">{esc(source.title or source.uri)}</a></li>'
        for source in brief.sources
    )
    scene_items = "".join(
        "<section><h2>" + esc(scene.heading) + "</h2><p>" + esc(" ".join(scene.lines)) +
        "</p><ul>" + "".join("<li>" + esc(note) + "</li>" for note in scene.notes) +
        "</ul><small>Claims: " + esc(", ".join(scene.claim_ids) or "Editorial framing") + "</small></section>"
        for scene in plan.scenes
    )
    packet = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Private video review</title><style>body{max-width:900px;margin:35px auto;padding:20px;background:#f4efe4;color:#28251d;'
        'font:17px Georgia,serif}video{width:100%;max-height:75vh;background:#181d1b}section{padding:20px 0;border-bottom:1px solid #ccbfa6}'
        'li{margin:9px 0}small{overflow-wrap:anywhere}a{color:#964222}</style>'
        '<h1>' + esc(storyboard.title) + '</h1><p>PRIVATE DRAFT. Not approved or published. Manufacturer claims are not hands-on tests. '
        'Abstract artwork is not product photography. This packet does not establish source or commercial reuse permission.</p>'
        '<video controls preload="metadata" poster="poster.png" src="draft.mp4"></video><h2>Source references</h2><ul>' +
        source_items + '</ul>' + scene_items +
        '<p>Exact draft SHA-256: <small>' + digest + '</small></p><p><a href="manifest.json">Full lineage manifest</a></p></html>'
    )
    (destination / "review.html").write_text(packet, encoding="utf-8")
    return {"family": plan.workflow_family, "movie": str(movie), "poster": str(destination / "poster.png"),
            "review": str(destination / "review.html"), "manifest": str(destination / "manifest.json"),
            "duration_seconds": plan.duration_seconds, "local_render_seconds": manifest["local_render_seconds"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard-id", action="append", required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / ".local" / "production-renders")
    parser.add_argument("--ffmpeg", type=Path, default=Path("/opt/homebrew/bin/ffmpeg"))
    args = parser.parse_args()
    if len(args.storyboard_id) > 3 or len(set(args.storyboard_id)) != len(args.storyboard_id):
        parser.error("Use one to three distinct storyboards per bounded local run.")
    if not args.ffmpeg.is_file():
        parser.error("The existing local ffmpeg binary is unavailable. Nothing was installed.")
    store = get_store()
    results = []
    for object_id in args.storyboard_id:
        result = export_one(store, object_id, args.output_root, args.ffmpeg)
        results.append(result)
        print(json.dumps(result), flush=True)
    print(json.dumps({"exports": len(results), "paid_api_calls": 0, "published": False}), flush=True)


if __name__ == "__main__":
    main()
