#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import subprocess
import sys
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIDTH = 1280
HEIGHT = 720
FPS = 24
SAMPLE_RATE = 22_050
DISPLAY_FONT = Path("/System/Library/Fonts/Avenir Next Condensed.ttc")
MONO_FONT = Path("/System/Library/Fonts/Menlo.ttc")
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,80}$")


@dataclass(frozen=True)
class Beat:
    image: str
    eyebrow: str
    headline: tuple[str, ...]
    deck: str
    accent: str
    duration: float
    layout: str
    number: str
    highlight_line: int


@dataclass
class BeatAssets:
    background: Image.Image
    eyebrow: Image.Image
    headline: list[Image.Image]
    deck: Image.Image | None
    number: Image.Image | None


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"Required local tool is missing: {name}")
    return path


def selected_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise RuntimeError(f"Required font is missing: {path}")
    return ImageFont.truetype(str(path), size=size, index=0)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def ease_out_back(value: float) -> float:
    value = clamp(value)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (value - 1) ** 3 + c1 * (value - 1) ** 2


def smoothstep(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def interpolate(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def parse_beat(payload: dict[str, Any], index: int) -> Beat:
    headline = payload.get("headline")
    if not isinstance(headline, list) or not 1 <= len(headline) <= 4:
        raise ValueError(f"Beat {index + 1} needs one to four headline lines")
    if not all(isinstance(line, str) and line.strip() for line in headline):
        raise ValueError(f"Beat {index + 1} has an invalid headline")
    image = str(payload.get("image", ""))
    if not image or Path(image).name != image:
        raise ValueError(f"Beat {index + 1} image must be a filename inside the assets directory")
    layout = str(payload.get("layout", "left"))
    if layout not in {"left", "right"}:
        raise ValueError(f"Beat {index + 1} layout must be left or right")
    duration = float(payload.get("duration", 0))
    if not 2 <= duration <= 12:
        raise ValueError(f"Beat {index + 1} duration must be between 2 and 12 seconds")
    accent = str(payload.get("accent", "#ff5c35"))
    ImageColor.getrgb(accent)
    highlight_line = int(payload.get("highlight_line", len(headline) - 1))
    if not 0 <= highlight_line < len(headline):
        raise ValueError(f"Beat {index + 1} highlight_line is outside the headline")
    return Beat(
        image=image,
        eyebrow=str(payload.get("eyebrow", "BS CATS / SMART GLASSES")),
        headline=tuple(line.strip() for line in headline),
        deck=str(payload.get("deck", "")).strip(),
        accent=accent,
        duration=duration,
        layout=layout,
        number=str(payload.get("number", "")).strip(),
        highlight_line=highlight_line,
    )


def load_spec(path: Path) -> tuple[dict[str, Any], list[Beat]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    video_id = str(payload.get("video_id", ""))
    if not SAFE_ID.fullmatch(video_id):
        raise ValueError("video_id must be a lowercase filesystem-safe identifier")
    raw_beats = payload.get("beats")
    if not isinstance(raw_beats, list) or not raw_beats:
        raise ValueError("The kinetic video needs at least one beat")
    beats = [parse_beat(item, index) for index, item in enumerate(raw_beats)]
    duration = sum(beat.duration for beat in beats)
    if not 60 <= duration <= 120:
        raise ValueError(f"Kinetic video duration must be 60-120 seconds, not {duration:.2f}")
    bpm = int(payload.get("bpm", 120))
    if not 80 <= bpm <= 150:
        raise ValueError("bpm must be between 80 and 150")
    payload["bpm"] = bpm
    return payload, beats


def fit_font(text: str, initial_size: int, maximum_width: int) -> ImageFont.FreeTypeFont:
    size = initial_size
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    while size >= 32:
        candidate = selected_font(DISPLAY_FONT, size)
        bounds = probe.textbbox((0, 0), text, font=candidate, stroke_width=2)
        if bounds[2] - bounds[0] <= maximum_width:
            return candidate
        size -= 4
    return selected_font(DISPLAY_FONT, 32)


def text_asset(
    text: str,
    *,
    size: int,
    fill: str,
    maximum_width: int,
    font_path: Path = DISPLAY_FONT,
    stroke_width: int = 0,
    stroke_fill: str = "#101820",
) -> Image.Image:
    if font_path == DISPLAY_FONT:
        face = fit_font(text, size, maximum_width)
    else:
        face = selected_font(font_path, size)
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    bounds = probe.textbbox((0, 0), text, font=face, stroke_width=stroke_width)
    width = max(1, bounds[2] - bounds[0] + 12)
    height = max(1, bounds[3] - bounds[1] + 12)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text(
        (6 - bounds[0], 6 - bounds[1]),
        text,
        font=face,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )
    return image


def prepare_background(path: Path) -> Image.Image:
    with Image.open(path) as source:
        return ImageOps.fit(
            source.convert("RGB"),
            (WIDTH + 120, HEIGHT + 68),
            method=Image.Resampling.LANCZOS,
        )


def prepare_assets(beats: list[Beat], assets_directory: Path) -> list[BeatAssets]:
    backgrounds: dict[str, Image.Image] = {}
    prepared: list[BeatAssets] = []
    for beat in beats:
        source_path = assets_directory / beat.image
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing kinetic background: {source_path}")
        if beat.image not in backgrounds:
            backgrounds[beat.image] = prepare_background(source_path)
        headline_assets = [
            text_asset(
                line,
                size=118 if len(beat.headline) <= 2 else 101,
                fill="#101820" if index == beat.highlight_line else "#ffffff",
                maximum_width=825,
                stroke_width=0 if index == beat.highlight_line else 2,
            )
            for index, line in enumerate(beat.headline)
        ]
        deck_asset = (
            text_asset(
                beat.deck.upper(),
                size=30,
                fill="#ffffff",
                maximum_width=850,
                font_path=MONO_FONT,
            )
            if beat.deck
            else None
        )
        number_asset = (
            text_asset(beat.number, size=260, fill="#ffffff", maximum_width=410)
            if beat.number
            else None
        )
        prepared.append(
            BeatAssets(
                background=backgrounds[beat.image],
                eyebrow=text_asset(
                    beat.eyebrow.upper(),
                    size=25,
                    fill="#ffffff",
                    maximum_width=700,
                    font_path=MONO_FONT,
                ),
                headline=headline_assets,
                deck=deck_asset,
                number=number_asset,
            )
        )
    return prepared


def shade_overlay(layout: str) -> Image.Image:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (8, 14, 18, 35))
    pixels = overlay.load()
    for x in range(WIDTH):
        position = x / max(1, WIDTH - 1)
        strength = (1 - position) if layout == "left" else position
        alpha = int(25 + 195 * strength**1.7)
        for y in range(HEIGHT):
            pixels[x, y] = (8, 14, 18, alpha)
    return overlay


def crop_background(background: Image.Image, progress: float, reverse: bool) -> Image.Image:
    progress = smoothstep(progress)
    if reverse:
        progress = 1 - progress
    maximum_x = background.width - WIDTH
    maximum_y = background.height - HEIGHT
    x = round(maximum_x * progress)
    y = round(maximum_y * (0.5 + 0.3 * math.sin(progress * math.pi * 2)))
    y = max(0, min(maximum_y, y))
    return background.crop((x, y, x + WIDTH, y + HEIGHT))


def paste_with_alpha(canvas: Image.Image, asset: Image.Image, x: int, y: int, opacity: float = 1.0) -> None:
    if opacity <= 0:
        return
    layer = asset
    if opacity < 0.999:
        layer = asset.copy()
        alpha = layer.getchannel("A").point(lambda value: round(value * opacity))
        layer.putalpha(alpha)
    canvas.alpha_composite(layer, (x, y))


def line_target(asset: Image.Image, layout: str) -> int:
    return 70 if layout == "left" else WIDTH - 70 - asset.width


def render_frame(
    beats: list[Beat],
    assets: list[BeatAssets],
    overlays: dict[str, Image.Image],
    beat_index: int,
    local_time: float,
) -> Image.Image:
    beat = beats[beat_index]
    beat_assets = assets[beat_index]
    progress = local_time / beat.duration
    base = crop_background(beat_assets.background, progress, reverse=beat_index % 2 == 1)
    transition_duration = 0.42
    if beat_index + 1 < len(beats) and local_time > beat.duration - transition_duration:
        transition = smoothstep((local_time - beat.duration + transition_duration) / transition_duration)
        following = crop_background(
            assets[beat_index + 1].background,
            transition * 0.08,
            reverse=(beat_index + 1) % 2 == 1,
        )
        base = Image.blend(base, following, transition)
    canvas = base.convert("RGBA")
    canvas.alpha_composite(overlays[beat.layout])
    draw = ImageDraw.Draw(canvas, "RGBA")
    accent = ImageColor.getrgb(beat.accent)

    pulse = 0.5 + 0.5 * math.sin(local_time * math.pi * 4)
    ribbon_width = round(190 + pulse * 80)
    if beat.layout == "left":
        draw.rectangle((0, 0, ribbon_width, 12), fill=(*accent, 255))
        draw.rectangle((WIDTH - 18, 0, WIDTH, HEIGHT), fill=(*accent, 210))
    else:
        draw.rectangle((WIDTH - ribbon_width, 0, WIDTH, 12), fill=(*accent, 255))
        draw.rectangle((0, 0, 18, HEIGHT), fill=(*accent, 210))

    wipe = 1 - smoothstep(local_time / 0.38)
    if wipe > 0:
        wipe_width = round(WIDTH * wipe)
        if beat.layout == "left":
            draw.polygon(
                ((0, 0), (wipe_width, 0), (max(0, wipe_width - 180), HEIGHT), (0, HEIGHT)),
                fill=(*accent, 235),
            )
        else:
            draw.polygon(
                ((WIDTH, 0), (WIDTH - wipe_width, 0), (min(WIDTH, WIDTH - wipe_width + 180), HEIGHT), (WIDTH, HEIGHT)),
                fill=(*accent, 235),
            )

    exit_progress = smoothstep((local_time - (beat.duration - 0.55)) / 0.55)
    opacity = 1 - exit_progress
    eyebrow_entry = ease_out_back((local_time - 0.08) / 0.5)
    eyebrow_target = line_target(beat_assets.eyebrow, beat.layout)
    eyebrow_start = -beat_assets.eyebrow.width - 80 if beat.layout == "left" else WIDTH + 80
    eyebrow_x = round(interpolate(eyebrow_start, eyebrow_target, eyebrow_entry))
    paste_with_alpha(canvas, beat_assets.eyebrow, eyebrow_x, 68, opacity)

    headline_height = sum(line.height for line in beat_assets.headline) + 18 * (len(beat_assets.headline) - 1)
    y = max(142, round((HEIGHT - headline_height) * 0.46))
    for line_index, line in enumerate(beat_assets.headline):
        entry = ease_out_back((local_time - 0.22 - line_index * 0.13) / 0.58)
        target_x = line_target(line, beat.layout)
        start_x = -line.width - 130 if beat.layout == "left" else WIDTH + 130
        x = round(interpolate(start_x, target_x, entry))
        if exit_progress:
            direction = 1 if beat.layout == "left" else -1
            x += round(direction * exit_progress * (WIDTH + line.width))
        if line_index == beat.highlight_line:
            padding_x = 15
            padding_y = 7
            draw.rounded_rectangle(
                (x - padding_x, y - padding_y, x + line.width + padding_x, y + line.height + padding_y),
                radius=8,
                fill=(*accent, round(248 * opacity)),
            )
        paste_with_alpha(canvas, line, x, y, opacity)
        y += line.height + 18

    if beat_assets.deck is not None:
        deck_entry = ease_out_back((local_time - 0.88) / 0.55)
        deck_target = line_target(beat_assets.deck, beat.layout)
        deck_start = -beat_assets.deck.width - 80 if beat.layout == "left" else WIDTH + 80
        deck_x = round(interpolate(deck_start, deck_target, deck_entry))
        paste_with_alpha(canvas, beat_assets.deck, deck_x, min(HEIGHT - 104, y + 24), opacity)

    if beat_assets.number is not None:
        number_opacity = 0.09 * smoothstep(local_time / 0.8) * opacity
        number_x = WIDTH - beat_assets.number.width - 34 if beat.layout == "left" else 34
        paste_with_alpha(canvas, beat_assets.number, number_x, 125, number_opacity)

    progress_right = round(WIDTH * ((beat_index + clamp(progress)) / len(beats)))
    draw.rectangle((0, HEIGHT - 9, WIDTH, HEIGHT), fill=(255, 255, 255, 65))
    draw.rectangle((0, HEIGHT - 9, progress_right, HEIGHT), fill=(*accent, 255))
    marker = f"{beat_index + 1:02d} / {len(beats):02d}"
    marker_font = selected_font(MONO_FONT, 19)
    draw.text((WIDTH - 28, HEIGHT - 27), marker, font=marker_font, fill=(255, 255, 255, 220), anchor="rs")
    return canvas.convert("RGB")


def synthesize_soundtrack(path: Path, duration: float, bpm: int) -> None:
    rng = random.Random(20260913)
    beat_seconds = 60 / bpm
    roots = (55.0, 65.41, 73.42, 49.0)
    frame_count = round(duration * SAMPLE_RATE)
    samples = array("h")
    for sample_index in range(frame_count):
        time = sample_index / SAMPLE_RATE
        beat_index = int(time / beat_seconds)
        beat_time = time - beat_index * beat_seconds
        bar_index = beat_index // 4
        root = roots[bar_index % len(roots)]

        bass_envelope = 0.45 + 0.55 * math.exp(-beat_time * 4.5)
        bass = math.sin(2 * math.pi * root * time) * 0.16 * bass_envelope
        fifth = math.sin(2 * math.pi * root * 1.5 * time + 0.4) * 0.035
        octave = math.sin(2 * math.pi * root * 2 * time + 1.1) * 0.025

        kick_phase = 2 * math.pi * (50 * beat_time + 3.4 * (1 - math.exp(-beat_time * 18)))
        kick = math.sin(kick_phase) * math.exp(-beat_time * 13) * 0.52

        eighth = beat_seconds / 2
        hat_time = time % eighth
        hat = rng.uniform(-1, 1) * math.exp(-hat_time * 75) * 0.075

        snare = 0.0
        if beat_index % 4 in {1, 3}:
            snare = rng.uniform(-1, 1) * math.exp(-beat_time * 24) * 0.16

        chapter_time = time % 6.0
        chapter_hit = math.sin(2 * math.pi * 180 * chapter_time) * math.exp(-chapter_time * 8) * 0.08
        value = bass + fifth + octave + kick + hat + snare + chapter_hit
        fade = min(1.0, time / 1.0, max(0.0, (duration - time) / 1.2))
        value = max(-0.95, min(0.95, value * fade))
        samples.append(round(value * 32767))

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(samples.tobytes())


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def build_captions(beats: list[Beat], output_path: Path) -> None:
    lines: list[str] = []
    timeline = 0.0
    for index, beat in enumerate(beats, start=1):
        end = timeline + beat.duration
        text = ". ".join((" ".join(beat.headline), beat.deck)).strip(". ")
        lines.extend(
            (
                str(index),
                f"{srt_timestamp(timeline)} --> {srt_timestamp(end)}",
                text,
                "",
            )
        )
        timeline = end
    output_path.write_text("\n".join(lines), encoding="utf-8")


def render_thumbnail(beat: Beat, assets: BeatAssets, output_path: Path) -> None:
    base = crop_background(assets.background, 0.42, reverse=False).convert("RGBA")
    base.alpha_composite(shade_overlay("left"))
    draw = ImageDraw.Draw(base, "RGBA")
    accent = ImageColor.getrgb(beat.accent)
    kicker = selected_font(MONO_FONT, 25)
    huge = selected_font(DISPLAY_FONT, 124)
    draw.text((58, 58), "SMART GLASSES / 2026 FIELD GUIDE", font=kicker, fill="#ffffff")
    draw.rounded_rectangle((48, 170, 700, 332), radius=12, fill=(*accent, 245))
    draw.text((70, 182), "4 TYPES.", font=huge, fill="#101820")
    draw.text((62, 344), "PICK 1.", font=huge, fill="#ffffff", stroke_width=2, stroke_fill="#101820")
    draw.rectangle((58, 535, 635, 541), fill=(*accent, 255))
    draw.text((60, 570), "PICK THE JOB. THEN PICK THE GLASSES.", font=kicker, fill="#ffffff")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output_path, format="PNG", optimize=True)


def render_video(
    spec_path: Path,
    assets_directory: Path,
    output_directory: Path,
) -> dict[str, Any]:
    ffmpeg = require_tool("ffmpeg")
    payload, beats = load_spec(spec_path)
    prepared = prepare_assets(beats, assets_directory)
    overlays = {"left": shade_overlay("left"), "right": shade_overlay("right")}
    duration = sum(beat.duration for beat in beats)
    output_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    soundtrack_path = output_directory / "original-soundtrack.wav"
    captions_path = output_directory / "captions.en.srt"
    base_video = output_directory / "kinetic-without-captions.mp4"
    final_video = output_directory / "demo.mp4"
    thumbnail_path = output_directory / "thumbnail.png"

    synthesize_soundtrack(soundtrack_path, duration, payload["bpm"])
    build_captions(beats, captions_path)
    render_thumbnail(beats[0], prepared[0], thumbnail_path)

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        f"{WIDTH}x{HEIGHT}",
        "-framerate",
        str(FPS),
        "-i",
        "pipe:0",
        "-i",
        str(soundtrack_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-af",
        "loudnorm=I=-18:LRA=8:TP=-1.5",
        "-shortest",
        str(base_video),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for beat_index, beat in enumerate(beats):
            print(f"[{beat_index + 1:02d}/{len(beats):02d}] {beat.headline[0]}", file=sys.stderr)
            frame_count = round(beat.duration * FPS)
            for frame_index in range(frame_count):
                local_time = frame_index / FPS
                frame = render_frame(beats, prepared, overlays, beat_index, local_time)
                process.stdin.write(frame.tobytes())
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait()
    except BrokenPipeError as exc:
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        process.wait()
        raise RuntimeError(f"FFmpeg stopped while receiving video frames: {stderr.strip()}") from exc
    if return_code != 0:
        raise RuntimeError(f"FFmpeg could not encode the kinetic video: {stderr.strip()}")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(base_video),
            "-i",
            str(captions_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-map",
            "1:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata",
            f"title={payload.get('working_title', payload['video_id'])}",
            "-metadata:s:s:0",
            "language=eng",
            str(final_video),
        ],
        check=True,
    )
    for artifact in (soundtrack_path, captions_path, base_video, final_video, thumbnail_path):
        artifact.chmod(0o600)
    return {
        "video_id": payload["video_id"],
        "video": str(final_video.resolve()),
        "thumbnail": str(thumbnail_path.resolve()),
        "captions": str(captions_path.resolve()),
        "soundtrack": str(soundtrack_path.resolve()),
        "duration_seconds": duration,
        "beats": len(beats),
        "voice": None,
        "paid_api_calls": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a voice-free kinetic text video locally.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--assets", type=Path, default=PROJECT_ROOT / ".local" / "assets" / "kinetic")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        payload, _ = load_spec(args.spec)
        output = args.output or PROJECT_ROOT / ".local" / "renders" / payload["video_id"]
        result = render_video(args.spec, args.assets, output)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
