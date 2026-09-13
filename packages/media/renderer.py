from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading

from PIL import Image, ImageDraw, ImageFont, ImageOps

from packages.contracts.media import RenderArtifactPayload
from packages.contracts.object import ActorType, UniversalObject
from packages.runtime.context import ROOT, fingerprint
from .planning import admit_recipe, file_hash

FPS = 24
COLOURS = {"orange": "#ff663f", "mint": "#bcf082", "cyan": "#58d2e8", "amber": "#ffca66"}
PRIMITIVE_VERSION = "image-primitives-1"


@dataclass
class Layer:
    image: Image.Image
    x: int
    y: int
    delay: float = 0.0


@lru_cache(maxsize=128)
def font(path, size):
    return ImageFont.truetype(path, size)


def glyph(text, path, size, width, height, colour="#ffffff"):
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    for point in range(max(12, int(size)), 11, -1):
        face = font(str(path), point)
        lines = []
        for paragraph in text.split("\n"):
            current = ""
            for word in paragraph.split():
                candidate = (current + " " + word).strip()
                if current and probe.textlength(candidate, font=face) > width - 8:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
        wrapped = "\n".join(lines)
        spacing = max(2, point // 8)
        box = probe.multiline_textbbox((0, 0), wrapped, font=face, spacing=spacing)
        w, h = math.ceil(box[2] - box[0]) + 8, math.ceil(box[3] - box[1]) + 8
        if w <= width and h <= height:
            sprite = Image.new("RGBA", (max(1, w), max(1, h)))
            ImageDraw.Draw(sprite).multiline_text((4-box[0], 4-box[1]), wrapped, font=face, fill=colour, spacing=spacing)
            return sprite
    raise ValueError("Text does not fit its primitive; revise the source-bound layout instead of truncating it.")


def background(asset, crop, width, height):
    with Image.open(ROOT / asset.asset_uri) as source:
        if source.width * source.height > 16_000_000:
            raise ValueError("Image dimensions exceed the bounded renderer budget.")
        source = source.convert("RGB")
        left, top, right, bottom = crop
        source = source.crop((round(left*source.width), round(top*source.height), round(right*source.width), round(bottom*source.height)))
        return ImageOps.fit(source, (width+80, height+46), method=Image.Resampling.LANCZOS)


def prepare_layers(beat, width, height, display, body):
    accent, margin = COLOURS[beat.accent], round(width*.045)
    layers = []
    label = glyph(beat.primitive.replace("_", " ").upper(), body, width*.023, width-2*margin, height*.08, accent)
    layers.append(Layer(label, margin, round(height*.10), .05))
    portrait = height > width
    if beat.primitive == "comparison_table":
        card_width = width-2*margin if portrait else (width-3*margin)//2
        card_height = round(height*.22) if portrait else round(height*.46)
        for index, cell in enumerate(beat.claim_cells):
            card = Image.new("RGBA", (card_width, card_height), (12, 23, 30, 224))
            draw = ImageDraw.Draw(card)
            draw.rectangle((0, 0, card_width, 5), fill=accent)
            title = glyph(cell.product_title.upper(), display, width*.035, card_width-24, card_height*.24)
            number = glyph(cell.value_display, display, width*.095, card_width-24, card_height*.46, accent)
            concept = glyph(cell.concept_label, body, width*.026, card_width-24, card_height*.19)
            card.alpha_composite(title, (12, 12))
            card.alpha_composite(number, (12, round(card_height*.29)))
            card.alpha_composite(concept, (12, round(card_height*.78)))
            x = margin if portrait else margin + index*(card_width+margin)
            y = round(height*.235) + index*(card_height+14) if portrait else round(height*.25)
            layers.append(Layer(card, x, y, .12 + index*.24))
        caption = glyph("MANUFACTURER STATEMENTS / NOT HANDS-ON TESTS", body, width*.023, width-2*margin, height*.09)
        layers.append(Layer(caption, margin, round(height*.76), .62))
    elif beat.primitive in {"decision_map", "timeline", "compatibility_chain"}:
        count = len(beat.lines)
        box_height = min(round(height*.20), round(height*.48/max(1, count)))
        for index, line in enumerate(beat.lines):
            plate = Image.new("RGBA", (width-2*margin, box_height), (12, 23, 30, 206))
            draw = ImageDraw.Draw(plate)
            if beat.primitive == "timeline":
                draw.line((18, 0, 18, box_height), fill=accent, width=3)
                draw.ellipse((11, 15, 25, 29), fill=accent)
            elif beat.primitive == "compatibility_chain":
                draw.polygon(((12, 12), (28, box_height//2), (12, box_height-12)), fill=accent)
            else:
                draw.rounded_rectangle((8, 10, 33, 35), radius=5, fill=accent)
            text = glyph(line, display, width*.060, width-2*margin-56, box_height-14)
            plate.alpha_composite(text, (44, 7))
            layers.append(Layer(plate, margin, round(height*.25)+index*(box_height+10), .12+index*.18))
    else:
        text = "\n".join(beat.lines)
        colour = accent if beat.primitive in {"question_hook", "feature_callout", "metric_card", "takeaway"} else "#ffffff"
        content = glyph(text, display, width*.082, width-2*margin, height*.49, colour)
        y = max(round(height*.24), round((height-content.height)*.48))
        if beat.primitive == "product_card":
            plate = Image.new("RGBA", (content.width+20, content.height+20), (12, 23, 30, 214))
            plate.alpha_composite(content, (10, 10))
            content = plate
        elif beat.primitive in {"feature_callout", "metric_card"}:
            stripe = Image.new("RGBA", (max(8, round(width*.012)), content.height), accent)
            layers.append(Layer(stripe, margin-12, y, .08))
        elif beat.primitive == "uncertainty_card":
            marker = Image.new("RGBA", (36, 36))
            ImageDraw.Draw(marker).polygon(((18, 1), (35, 35), (1, 35)), fill=accent)
            layers.append(Layer(marker, width-margin-40, round(height*.16), .05))
        elif beat.primitive == "evidence_note":
            line = Image.new("RGBA", (width-2*margin, 3), accent)
            layers.append(Layer(line, margin, y-12, .05))
        elif beat.primitive in {"question_reveal", "takeaway"}:
            line = Image.new("RGBA", (min(content.width, width//2), 5), accent)
            layers.append(Layer(line, margin, y+content.height+12, .45))
        layers.append(Layer(content, margin, y, .15))
    return layers


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


def frame_for(beat, bg, layers, shade, notice, width, height, local_time, elapsed, total_duration, index):
    progress = smooth(local_time/beat.duration_seconds)
    x = round(80 * (progress if index % 2 else 1-progress))
    y = round(23 + 18*math.sin(progress*math.pi))
    canvas = bg.crop((x, y, x+width, y+height)).convert("RGBA")
    canvas.alpha_composite(shade)
    for layer in layers:
        entry = smooth((local_time-layer.delay)/.38)
        opacity = entry*(1-smooth((local_time-beat.duration_seconds+.24)/.24))
        if opacity <= 0:
            continue
        image = layer.image
        if opacity < .999:
            image = image.copy()
            image.putalpha(image.getchannel("A").point(lambda alpha: round(alpha*opacity)))
        offset = round((1-entry)*42) * (1 if index % 2 else -1)
        canvas.alpha_composite(image, (layer.x+offset, layer.y))
    draw = ImageDraw.Draw(canvas)
    accent = COLOURS[beat.accent]
    pulse = .5+.5*math.sin(local_time*math.pi*4)
    draw.rectangle((0, 0, round(width*(.10+.04*pulse)), 6), fill=accent)
    draw.rectangle((0, height-5, width, height), fill=(255,255,255,75))
    draw.rectangle((0, height-5, round(width*min(1,(elapsed+local_time)/total_duration)), height), fill=accent)
    canvas.alpha_composite(notice, (round(width*.045), height-notice.height-12))
    return canvas.convert("RGB")


def render(store, recipe, *, quality="preview", timeout_seconds=180):
    from scripts.render_kinetic_video import synthesize_soundtrack

    payload = admit_recipe(store, recipe)
    if quality not in {"preview", "review"}:
        raise ValueError("Choose a bounded private preview or review render.")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("The renderer requires the existing FFmpeg and FFprobe tools.")
    width, height = (768,432) if quality == "preview" else (1280,720)
    if payload.aspect_ratio == "9:16":
        width, height = height, width
    display = ROOT / payload.assets[payload.display_font_asset_id].asset_uri
    body = ROOT / payload.assets[payload.body_font_asset_id].asset_uri
    prepared = [(background(payload.assets[beat.image_asset_id], beat.crop, width, height),
                 prepare_layers(beat, width, height, display, body)) for beat in payload.beats]
    alpha = Image.new("L", (width,1))
    alpha.putdata([round(195-125*(x/max(1,width-1))**.7) for x in range(width)])
    shade = Image.new("RGBA", (width,height), (5,13,21,0))
    shade.putalpha(alpha.resize((width,height)))
    notice = glyph("PRIVATE REVIEW / CONCEPT IMAGERY, NOT PRODUCT PHOTOGRAPHY", body, width*.021, width*.91, height*.065)
    root = ROOT / ".local/production-renders"
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="image-kinetic-", dir=root))
    folder.chmod(0o700)
    soundtrack, video, poster = folder/"soundtrack.wav", folder/"draft.mp4", folder/"poster.png"
    synthesize_soundtrack(soundtrack, payload.duration_seconds, 120)
    frame_for(payload.beats[0], *prepared[0], shade, notice, width, height, 1.2, 0, payload.duration_seconds, 0).save(poster)
    command = [ffmpeg,"-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}","-r",str(FPS),"-i","pipe:0","-i",str(soundtrack),
               "-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p","-threads","2",
               "-c:a","aac","-b:a","128k","-af","alimiter=limit=0.85","-t",str(payload.duration_seconds),"-movflags","+faststart",str(video)]
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C", "LC_ALL": "C"}
    with (folder/"encoder.log").open("wb") as error_log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=error_log, env=environment, start_new_session=True)
        def stop_encoder():
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        timer = threading.Timer(min(240, max(10, timeout_seconds)), stop_encoder)
        timer.daemon = True
        timer.start()
        try:
            elapsed, prior_frame = 0.0, 0
            for index, beat in enumerate(payload.beats):
                end_frame = round((elapsed+beat.duration_seconds)*FPS)
                print(json.dumps({"beat":index+1,"of":len(payload.beats),"primitive":beat.primitive}), flush=True)
                for frame_index in range(end_frame-prior_frame):
                    image = frame_for(beat, *prepared[index], shade, notice, width, height, frame_index/FPS, elapsed, payload.duration_seconds, index)
                    process.stdin.write(image.tobytes())
                elapsed += beat.duration_seconds
                prior_frame = end_frame
            process.stdin.close()
            if process.wait(timeout=15) != 0:
                raise RuntimeError("The bounded encoder failed; no approved artifact was created.")
        except BaseException:
            stop_encoder()
            process.wait(timeout=5)
            raise
        finally:
            timer.cancel()
    probe = subprocess.run([ffprobe,"-v","error","-show_entries","format=duration:stream=codec_type,codec_name,width,height","-of","json",str(video)], capture_output=True, text=True, check=True, timeout=15, env=environment)
    report = json.loads(probe.stdout)
    actual_duration = float(report["format"]["duration"])
    has_audio = any(stream["codec_type"] == "audio" for stream in report["streams"])
    if not has_audio or abs(actual_duration-payload.duration_seconds) > .12:
        raise ValueError("Media QA did not establish the required soundtrack and duration.")
    # Recheck inputs after encoding; a changing source cannot silently produce an
    # approvable artifact from a stale plan.
    admit_recipe(store, recipe)
    metadata = {"title": recipe.title.removeprefix("Image-led recipe: "),
                "description": "Private evidence-linked comparison draft. Manufacturer statements are not hands-on tests. Concept imagery is not product photography. No sponsorship or active affiliate relationship is asserted.",
                "visibility": "not_uploaded", "publication_allowed": False}
    manifest = {"schema_version":"render-manifest-1", "recipe_object_id":recipe.object_id,"recipe_version":recipe.version,
                "recipe_sha256":fingerprint(recipe.payload), "recipe":payload.model_dump(mode="json"),
                "video_sha256":file_hash(video),"soundtrack_sha256":file_hash(soundtrack),
                "primitive_registry_version":PRIMITIVE_VERSION,"primitives_used":sorted({beat.primitive for beat in payload.beats}),
                "creative_profile_revision":payload.creative_profile_revision,"publish_metadata":metadata,
                "metadata_sha256":fingerprint(metadata),"media_qa":report,"duration_seconds":actual_duration,
                "provider_calls":0,"all_operating_costs_known":False,"publication_allowed":False,
                "rights_gate":"Legacy image provenance is not cleared for publication.",
                "factual_gate":"Source-bound statements still require factual review.","human_exact_artifact_approval":"not_granted"}
    manifest_path = folder/"manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True))
    for path in (video,poster,soundtrack,manifest_path,folder/"encoder.log"):
        path.chmod(0o600)
    artifact_payload = RenderArtifactPayload(summary="Private image-led, music-backed video bound to its recipe and exact output bytes.",
        recipe_object_id=recipe.object_id, recipe_version=recipe.version,
        artifact_uri=str(video.relative_to(ROOT)),poster_uri=str(poster.relative_to(ROOT)),manifest_uri=str(manifest_path.relative_to(ROOT)),
        video_sha256=manifest["video_sha256"],manifest_sha256=file_hash(manifest_path),metadata_sha256=manifest["metadata_sha256"],
        publish_metadata=metadata,duration_seconds=actual_duration,width=width,height=height)
    identifier = "render_" + fingerprint({"video":manifest["video_sha256"],"recipe":recipe.object_id})[:32]
    artifact = UniversalObject(object_id=identifier,object_type="render_artifact",title=("Video draft: "+metadata["title"])[:240],
        purpose="Inspect the exact image/music artifact, metadata, provenance and gates before any release decision.",
        parent_ids=[recipe.object_id],sources=recipe.sources,payload=artifact_payload.model_dump(mode="json"),
        metadata={"publication_allowed":False,"source_versions":{recipe.object_id:recipe.version},"creative_profile_revision":payload.creative_profile_revision})
    store.capture(artifact,actor_id="agent:local-renderer",actor_type=ActorType.agent,idempotency_key="render-"+identifier,
                  request_input={"recipe_id":recipe.object_id,"video_sha256":manifest["video_sha256"],"manifest_sha256":file_hash(manifest_path)})
    return {"artifact_id":identifier,"video":str(video),"poster":str(poster),"manifest":str(manifest_path),
            "duration_seconds":actual_duration,"audio_present":has_audio,"publication_allowed":False,
            "review_url":"http://127.0.0.1:8766/media-review/"+identifier}
