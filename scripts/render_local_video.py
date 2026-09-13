#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts.content import VideoScene, VideoScript  # noqa: E402


WIDTH = 1280
HEIGHT = 720
FPS = 24
FONT_ROOT = PROJECT_ROOT / "assets" / "fonts" / "barlow-condensed"
DISPLAY_FONT = FONT_ROOT / "BarlowCondensed-ExtraBold.ttf"
SANS_FONT = FONT_ROOT / "BarlowCondensed-Medium.ttf"
MONO_FONT = FONT_ROOT / "BarlowCondensed-Medium.ttf"
PALETTES = [
    ("#F2E9D5", "#15242E", "#E95135", "#1D6F8A"),
    ("#DDE9F0", "#112532", "#E85D35", "#2C6E49"),
    ("#F3E4D7", "#1A2530", "#D64045", "#20639B"),
    ("#E5E1D8", "#17212B", "#E76F51", "#287271"),
]


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"Required local tool is missing: {name}")
    return path


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def font(path: Path, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    if not path.exists():
        raise RuntimeError(f"Required font is missing: {path}")
    return ImageFont.truetype(str(path), size=size, index=index)


def wrap_by_width(
    draw: ImageDraw.ImageDraw,
    value: str,
    selected_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(candidate, font=selected_font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def draw_grid(draw: ImageDraw.ImageDraw, color: str) -> None:
    for x in range(0, WIDTH, 64):
        draw.line((x, 0, x, HEIGHT), fill=color, width=1)
    for y in range(0, HEIGHT, 64):
        draw.line((0, y, WIDTH, y), fill=color, width=1)


def draw_category_art(
    draw: ImageDraw.ImageDraw,
    scene_index: int,
    ink: str,
    accent: str,
    secondary: str,
) -> None:
    left, top, right, bottom = 790, 150, 1185, 555
    draw.rounded_rectangle((left, top, right, bottom), radius=34, outline=ink, width=5)
    mode = scene_index % 8
    if mode == 0:
        for row in range(2):
            for column in range(2):
                x = left + 38 + column * 180
                y = top + 38 + row * 175
                draw.rounded_rectangle((x, y, x + 140, y + 130), radius=20, fill=(accent if (row + column) % 2 == 0 else secondary))
    elif mode == 1:
        draw.line((left + 195, top + 55, left + 195, bottom - 45), fill=ink, width=16)
        for offset, direction in ((90, -1), (180, 1), (270, -1)):
            y = top + offset
            end_x = left + 60 if direction < 0 else right - 60
            draw.line((left + 195, y, end_x, y), fill=accent if direction < 0 else secondary, width=22)
    elif mode == 2:
        draw.ellipse((left + 65, top + 95, left + 185, top + 215), outline=accent, width=20)
        draw.ellipse((right - 185, top + 95, right - 65, top + 215), outline=accent, width=20)
        draw.line((left + 185, top + 155, right - 185, top + 155), fill=ink, width=16)
        for radius in (40, 75, 110):
            draw.arc((left + 140 - radius, top + 235 - radius, left + 140 + radius, top + 235 + radius), 310, 50, fill=secondary, width=8)
    elif mode == 3:
        draw.rounded_rectangle((left + 48, top + 65, right - 48, bottom - 65), radius=24, fill="#0E241F")
        for index, width in enumerate((230, 280, 180)):
            y = top + 125 + index * 75
            draw.rounded_rectangle((left + 80, y, left + 80 + width, y + 22), radius=11, fill="#63E6A3")
    elif mode == 4:
        draw.rounded_rectangle((left + 55, top + 70, right - 55, bottom - 80), radius=18, fill=ink)
        draw.rounded_rectangle((left + 82, top + 97, right - 82, bottom - 107), radius=10, fill=secondary)
        draw.line((left + 195, bottom - 80, left + 195, bottom - 35), fill=ink, width=14)
        draw.line((left + 115, bottom - 35, right - 115, bottom - 35), fill=ink, width=14)
    elif mode == 5:
        for step in range(6):
            inset = 35 + step * 25
            draw.rectangle((left + inset, top + inset, right - inset, bottom - inset), outline=secondary if step % 2 else accent, width=4)
        draw.ellipse((left + 160, top + 160, right - 160, bottom - 160), fill=accent)
    elif mode == 6:
        for index in range(4):
            y = top + 65 + index * 78
            draw.rounded_rectangle((left + 55, y, left + 95, y + 40), radius=6, outline=ink, width=5)
            draw.line((left + 68, y + 21, left + 78, y + 31, left + 102, y + 7), fill=accent, width=7)
            draw.line((left + 125, y + 20, right - 55, y + 20), fill=secondary, width=12)
    else:
        draw.line((left + 65, top + 205, right - 65, top + 205), fill=ink, width=18)
        draw.polygon(((right - 105, top + 165), (right - 55, top + 205), (right - 105, top + 245)), fill=ink)
        draw.ellipse((left + 130, top + 140, left + 260, top + 270), fill=accent)


def render_scene_frame(
    scene: VideoScene,
    scene_index: int,
    scene_count: int,
    output_path: Path,
) -> None:
    background, ink, accent, secondary = PALETTES[scene_index % len(PALETTES)]
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)
    grid_color = "#D6CDBD" if scene_index % 2 == 0 else "#C9D7DF"
    draw_grid(draw, grid_color)
    draw.rectangle((0, 0, WIDTH, 18), fill=accent)
    draw.rectangle((0, HEIGHT - 52, WIDTH, HEIGHT), fill=ink)

    label_font = font(SANS_FONT, 25)
    title_font = font(DISPLAY_FONT, 58)
    small_font = font(SANS_FONT, 23)
    mono_font = font(MONO_FONT, 17)
    number_font = font(SANS_FONT, 138)

    draw.text((65, 52), "BS CATS / SMART GLASSES FIELD GUIDE", font=label_font, fill=ink)
    draw.text((1110, 32), f"{scene_index + 1:02d}", font=number_font, fill=accent, anchor="ma")

    scene_title = scene.scene_id.replace("_", " ").upper()
    draw.text((65, 116), scene_title, font=small_font, fill=secondary)
    primary = scene.on_screen_text[0] if scene.on_screen_text else scene_title
    primary_lines = wrap_by_width(draw, primary, title_font, 650)
    y = 170
    for line in primary_lines[:4]:
        draw.text((65, y), line, font=title_font, fill=ink)
        y += 68

    for line in scene.on_screen_text[1:4]:
        wrapped = wrap_by_width(draw, line, small_font, 630)
        for part in wrapped:
            draw.rounded_rectangle((65, y + 8, 82, y + 25), radius=8, fill=accent)
            draw.text((96, y), part, font=small_font, fill=ink)
            y += 36

    draw_category_art(draw, scene_index, ink, accent, secondary)
    evidence_label = f"{len(scene.claim_ids)} LINKED CLAIM{'S' if len(scene.claim_ids) != 1 else ''}" if scene.claim_ids else "EDITORIAL"
    draw.text((65, HEIGHT - 35), evidence_label, font=mono_font, fill="#FFFFFF", anchor="lm")
    draw.text((WIDTH - 65, HEIGHT - 35), f"SCENE {scene_index + 1} / {scene_count}", font=mono_font, fill="#FFFFFF", anchor="rm")
    progress_right = 65 + int((WIDTH - 130) * ((scene_index + 1) / scene_count))
    draw.rectangle((65, HEIGHT - 10, WIDTH - 65, HEIGHT - 6), fill="#59636A")
    draw.rectangle((65, HEIGHT - 10, progress_right, HEIGHT - 6), fill=accent)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)


def render_thumbnail(script: VideoScript, output_path: Path) -> None:
    background, ink, accent, secondary = PALETTES[0]
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)
    draw_grid(draw, "#D6CDBD")
    draw.rectangle((0, 0, WIDTH, 24), fill=accent)
    label_font = font(SANS_FONT, 30)
    huge_font = font(SANS_FONT, 112)
    draw.text((60, 55), "SMART GLASSES / 2026 FIELD GUIDE", font=label_font, fill=ink)
    words = script.thumbnail_text.split()
    first = " ".join(words[:2]) if len(words) > 2 else words[0]
    second = " ".join(words[2:]) if len(words) > 2 else " ".join(words[1:])
    draw.text((60, 145), first, font=huge_font, fill=ink)
    draw.text((60, 270), second, font=huge_font, fill=accent)
    labels = ("CAPTURE", "GLANCE", "SCREEN", "BUILD")
    for index, label in enumerate(labels):
        x = 60 + index * 292
        color = accent if index % 2 == 0 else secondary
        draw.rounded_rectangle((x, 500, x + 252, 625), radius=18, fill=color)
        draw.text((x + 126, 564), label, font=label_font, fill="#FFFFFF", anchor="mm")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)


def media_duration(ffprobe: str, path: Path) -> float:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    candidates = [payload.get("format", {}).get("duration")]
    candidates.extend(stream.get("duration") for stream in payload.get("streams", []))
    durations: list[float] = []
    for candidate in candidates:
        try:
            duration = float(candidate)
        except (TypeError, ValueError):
            continue
        if math.isfinite(duration) and duration > 0:
            durations.append(duration)
    if not durations:
        raise RuntimeError(
            f"Narration contains no measurable audio: {path}. "
            "On macOS, run the renderer where the built-in speech service is available."
        )
    return max(durations)


def caption_chunks(text: str, max_words: int = 12) -> list[str]:
    words = text.split()
    return [" ".join(words[index : index + max_words]) for index in range(0, len(words), max_words)]


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def build_captions(script: VideoScript, durations: list[float], output_path: Path) -> None:
    cues: list[str] = []
    timeline = 0.0
    cue_number = 1
    for scene, duration in zip(script.scenes, durations, strict=True):
        chunks = caption_chunks(scene.narration)
        weights = [max(1, len(chunk.split())) for chunk in chunks]
        total_weight = sum(weights)
        cursor = timeline
        for chunk, weight in zip(chunks, weights, strict=True):
            chunk_duration = duration * weight / total_weight
            end = cursor + chunk_duration
            cues.extend(
                [
                    str(cue_number),
                    f"{srt_timestamp(cursor)} --> {srt_timestamp(end)}",
                    chunk,
                    "",
                ]
            )
            cue_number += 1
            cursor = end
        timeline += duration
    output_path.write_text("\n".join(cues), encoding="utf-8")


def render_video(
    script_path: Path,
    output_directory: Path,
    *,
    voice: str = "Daniel",
    speech_rate: int = 170,
) -> dict[str, Any]:
    ffmpeg = require_tool("ffmpeg")
    ffprobe = require_tool("ffprobe")
    say = require_tool("say")
    script = VideoScript.model_validate_json(script_path.read_text(encoding="utf-8"))

    frames_directory = output_directory / "frames"
    audio_directory = output_directory / "audio"
    clips_directory = output_directory / "clips"
    for directory in (frames_directory, audio_directory, clips_directory):
        directory.mkdir(parents=True, exist_ok=True)

    durations: list[float] = []
    clip_paths: list[Path] = []
    for index, scene in enumerate(script.scenes):
        stem = f"{index + 1:02d}-{scene.scene_id}"
        frame_path = frames_directory / f"{stem}.png"
        audio_path = audio_directory / f"{stem}.aiff"
        clip_path = clips_directory / f"{stem}.mp4"
        render_scene_frame(scene, index, len(script.scenes), frame_path)
        run([say, "-v", voice, "-r", str(speech_rate), "-o", str(audio_path), scene.narration])
        duration = media_duration(ffprobe, audio_path)
        durations.append(duration)
        clip_paths.append(clip_path)
        fade_out = max(0.0, duration - 0.3)
        video_filter = (
            "scale=1320:742,"
            "crop=1280:720:x='(iw-ow)/2+8*sin(t/4)':y='(ih-oh)/2+5*cos(t/5)',"
            "fade=t=in:st=0:d=0.3,"
            f"fade=t=out:st={fade_out:.3f}:d=0.3,format=yuv420p"
        )
        run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-loop",
                "1",
                "-framerate",
                str(FPS),
                "-i",
                str(frame_path),
                "-i",
                str(audio_path),
                "-t",
                f"{duration:.3f}",
                "-vf",
                video_filter,
                "-af",
                "loudnorm=I=-16:LRA=11:TP=-1.5",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-r",
                str(FPS),
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-ar",
                "48000",
                "-shortest",
                str(clip_path),
            ]
        )

    concat_path = output_directory / "concat.txt"
    concat_path.write_text(
        "\n".join(f"file '{path.resolve().as_posix()}'" for path in clip_paths) + "\n",
        encoding="utf-8",
    )
    base_video = output_directory / "video-without-captions.mp4"
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            str(base_video),
        ]
    )

    captions_path = output_directory / "captions.en.srt"
    build_captions(script, durations, captions_path)
    final_video = output_directory / "demo.mp4"
    run(
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
            f"title={script.working_title}",
            "-metadata:s:s:0",
            "language=eng",
            str(final_video),
        ]
    )
    thumbnail_path = output_directory / "thumbnail.png"
    render_thumbnail(script, thumbnail_path)
    return {
        "script_id": script.script_id,
        "video": str(final_video),
        "captions": str(captions_path),
        "thumbnail": str(thumbnail_path),
        "duration_seconds": round(sum(durations), 2),
        "voice": voice,
        "speech_rate": speech_rate,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a zero-API-cost local narrated demo video."
    )
    parser.add_argument("script", type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--voice", default="Daniel")
    parser.add_argument("--speech-rate", type=int, default=170)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    script_id = VideoScript.model_validate_json(
        args.script.read_text(encoding="utf-8")
    ).script_id
    output_directory = args.output_directory or (
        PROJECT_ROOT / ".local" / "renders" / script_id
    )
    try:
        result = render_video(
            args.script,
            output_directory,
            voice=args.voice,
            speech_rate=args.speech_rate,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
