#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts import LocalObjectStore  # noqa: E402
from packages.contracts.content import VideoScript  # noqa: E402


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_uri(target: Path, output: Path) -> str:
    return Path(os.path.relpath(target.resolve(), output.parent.resolve())).as_posix()


def package_demo_artifacts(
    video_path: Path,
    captions_path: Path,
    thumbnail_path: Path,
    review_packet_path: Path,
    output_path: Path,
) -> tuple[Path, Path, Path, Path]:
    assets_directory = output_path.parent / "assets"
    assets_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    packaged_video = assets_directory / "demo.mp4"
    packaged_captions = assets_directory / "captions.en.vtt"
    packaged_thumbnail = assets_directory / "thumbnail.png"
    packaged_review = assets_directory / "founder-review.html"

    shutil.copyfile(video_path, packaged_video)
    shutil.copyfile(thumbnail_path, packaged_thumbnail)
    shutil.copyfile(review_packet_path, packaged_review)
    srt = captions_path.read_text(encoding="utf-8")
    webvtt = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt)
    packaged_captions.write_text(f"WEBVTT\n\n{webvtt}", encoding="utf-8")
    for artifact in (packaged_video, packaged_captions, packaged_thumbnail, packaged_review):
        os.chmod(artifact, 0o600)
    return packaged_video, packaged_captions, packaged_thumbnail, packaged_review


def build_dashboard(
    script_path: Path,
    store_path: Path,
    video_path: Path,
    captions_path: Path,
    thumbnail_path: Path,
    review_packet_path: Path,
    output_path: Path,
) -> None:
    script = VideoScript.model_validate_json(script_path.read_text(encoding="utf-8"))
    store = LocalObjectStore(store_path)
    brief = store.get(script.brief_object_id)
    script_object = store.get(script.script_id)
    source_count = len(brief.sources)
    claim_count = len(brief.payload.get("claims", []))
    history_count = len(store.history(brief.object_id)) + len(store.history(script.script_id))

    packaged = package_demo_artifacts(
        video_path,
        captions_path,
        thumbnail_path,
        review_packet_path,
        output_path,
    )
    video_uri, captions_uri, thumbnail_uri, review_uri = (
        escape(relative_uri(path, output_path)) for path in packaged
    )
    stages = [
        ("01", "Research", f"{source_count} sources captured", "complete"),
        ("02", "Evidence", f"{claim_count} linked claims", "complete"),
        ("03", "Curation", f"Brief v{brief.version} · {brief.status.value}", "complete"),
        ("04", "Production", f"Script v{script_object.version} · local MP4", "complete"),
        ("05", "Distribution", "Human approval required", "locked"),
    ]
    stage_markup = "".join(
        f"""
        <article class="stage {state}">
          <span>{number}</span><div><h3>{escape(name)}</h3><p>{escape(detail)}</p></div>
        </article>
        """
        for number, name, detail, state in stages
    )
    source_markup = "".join(
        f'<li><a href="{escape(source.uri)}" rel="noreferrer">{escape(source.publisher or source.title or source.source_id)}</a></li>'
        for source in brief.sources
    )
    document = f"""<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>BS CATS · Working Demo</title>
  <style>
    :root {{ --night:#13232d; --paper:#f3ead7; --orange:#ef5a38; --aqua:#75d5c4; --blue:#286c86; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--night); font-family:"Iowan Old Style","Palatino Linotype",serif; }}
    .shell {{ width:min(1240px,calc(100% - 28px)); margin:20px auto 70px; }}
    header {{ display:grid; grid-template-columns:1.3fr .7fr; background:var(--night); color:white; min-height:360px; overflow:hidden; }}
    .hero-copy {{ padding:clamp(28px,6vw,72px); }}
    .kicker,.stage span,.lock,.metric strong {{ font-family:"Avenir Next Condensed",sans-serif; text-transform:uppercase; letter-spacing:.08em; }}
    h1 {{ font-size:clamp(3rem,7vw,6.8rem); line-height:.88; margin:.2em 0; font-weight:600; }}
    .hero-art {{ background:var(--orange); display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:8px; transform:rotate(4deg) scale(1.08); }}
    .hero-art div {{ background:var(--paper); display:grid; place-items:center; font:800 clamp(1rem,2.3vw,2rem)/1 "Avenir Next Condensed",sans-serif; }}
    .hero-art div:nth-child(2),.hero-art div:nth-child(3) {{ background:var(--blue); color:white; }}
    .metrics {{ display:grid; grid-template-columns:repeat(4,1fr); margin-top:20px; gap:10px; }}
    .metric {{ border:1px solid #bcae95; background:#fff9ed; padding:20px; }}
    .metric strong {{ display:block; font-size:2rem; color:var(--orange); }}
    section {{ margin-top:54px; }}
    h2 {{ font-size:clamp(2rem,4vw,4rem); margin:0 0 18px; border-bottom:3px solid var(--night); }}
    video {{ width:100%; background:black; box-shadow:12px 12px 0 var(--blue); }}
    .pipeline {{ display:grid; gap:8px; }}
    .stage {{ display:grid; grid-template-columns:72px 1fr; align-items:center; border:1px solid #bcae95; background:#fff9ed; padding:18px; }}
    .stage span {{ font-size:2rem; color:var(--blue); }}
    .stage h3,.stage p {{ margin:.1rem 0; }}
    .stage.locked {{ background:#fee4db; border-color:var(--orange); }}
    .stage.locked span {{ color:var(--orange); }}
    .two {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; }}
    .card {{ background:#fff9ed; border:1px solid #bcae95; padding:24px; }}
    .lock {{ display:inline-block; background:var(--orange); color:white; padding:8px 12px; font-weight:800; }}
    a {{ color:#155e75; font-weight:700; }}
    li {{ margin:.7rem 0; overflow-wrap:anywhere; }}
    @media(max-width:760px) {{ header,.two {{ grid-template-columns:1fr; }} .hero-art {{ min-height:220px; }} .metrics {{ grid-template-columns:1fr 1fr; }} }}
  </style>
</head><body><main class="shell">
  <header><div class="hero-copy"><div class="kicker">Local-first · evidence-linked · human-gated</div><h1>Working demo.</h1><p>One source trail becomes a reviewable brief, script, original imagery, kinetic typography, soundtrack, captions, and playable video without a paid API call.</p><span class="lock">External publishing locked</span></div><div class="hero-art"><div>CAPTURE</div><div>CURATE</div><div>CREATE</div><div>CONTROL</div></div></header>
  <div class="metrics"><div class="metric"><strong>{source_count}</strong>sources</div><div class="metric"><strong>{claim_count}</strong>claims</div><div class="metric"><strong>{len(script.scenes)}</strong>scenes</div><div class="metric"><strong>{history_count}</strong>audit events</div></div>
  <section><h2>The generated result</h2><video controls preload="metadata" poster="{thumbnail_uri}"><source src="{video_uri}" type="video/mp4"><track kind="captions" srclang="en" label="English" src="{captions_uri}" default></video><p><a href="{review_uri}">Open the detailed founder review packet</a></p></section>
  <section><h2>End-to-end pipeline</h2><div class="pipeline">{stage_markup}</div></section>
  <section class="two"><article class="card"><h2>What is real</h2><p>The object IDs, provenance links, claim policy, lifecycle transitions, original visual assets, kinetic motion, soundtrack, captions, MP4, and audit history are generated artifacts on this machine. No copied product footage or synthetic hands-on claim is used.</p></article><article class="card"><h2>What stays gated</h2><p>YouTube, LinkedIn, public hosting, affiliate links, and paid generation remain disabled until the local result is worth publishing and all freshness-sensitive facts are checked.</p></article></section>
  <section><h2>Source trail</h2><ol>{source_markup}</ol></section>
</main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    os.chmod(output_path, 0o600)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the local end-to-end demo dashboard.")
    parser.add_argument("script", type=Path)
    parser.add_argument("--store", type=Path, default=PROJECT_ROOT / ".local" / "object-events.jsonl")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--captions", type=Path, required=True)
    parser.add_argument("--thumbnail", type=Path, required=True)
    parser.add_argument("--review-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / ".local" / "demo" / "index.html")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        build_dashboard(
            args.script,
            args.store,
            args.video,
            args.captions,
            args.thumbnail,
            args.review_packet,
            args.output,
        )
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"demo": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
