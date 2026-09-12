#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import ValidationError  # noqa: E402

from packages.contracts import (  # noqa: E402
    ActorType,
    CurationPatch,
    LocalObjectStore,
    ObjectStoreError,
    UniversalObject,
)
from packages.contracts.content import VideoScript  # noqa: E402


def validate_script_against_brief(
    script: VideoScript, brief: UniversalObject
) -> dict[str, dict[str, Any]]:
    if script.brief_object_id != brief.object_id:
        raise ValueError("script brief_object_id does not match the loaded brief")
    raw_claims = brief.payload.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ValueError("brief payload claims must be a list")
    claims = {
        claim.get("claim_id"): claim
        for claim in raw_claims
        if isinstance(claim, dict) and claim.get("claim_id")
    }
    unknown_claims = {
        claim_id
        for scene in script.scenes
        for claim_id in scene.claim_ids
        if claim_id not in claims
    }
    if unknown_claims:
        raise ValueError("script contains claim IDs that are absent from the brief")

    source_ids = {source.source_id for source in brief.sources}
    unknown_sources = {
        source_id
        for scene in script.scenes
        for claim_id in scene.claim_ids
        for source_id in claims[claim_id].get("source_ids", [])
        if source_id not in source_ids
    }
    if unknown_sources:
        raise ValueError("script claims reference sources that are absent from the brief")
    return claims


def _safe_link(uri: str) -> str | None:
    parsed = urlsplit(uri)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return uri
    return None


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_review_packet(
    script: VideoScript,
    brief: UniversalObject,
    output_path: Path,
) -> None:
    claims = validate_script_against_brief(script, brief)
    claim_ids_used = {
        claim_id for scene in script.scenes for claim_id in scene.claim_ids
    }
    source_ids_used = {
        source_id
        for claim_id in claim_ids_used
        for source_id in claims[claim_id].get("source_ids", [])
    }
    sources = [source for source in brief.sources if source.source_id in source_ids_used]

    scene_html = []
    elapsed = 0
    for index, scene in enumerate(script.scenes, start=1):
        starts_at = elapsed
        elapsed += scene.duration_seconds
        claim_badges = "".join(
            f'<span class="claim-chip">{_escape(claim_id)}</span>'
            for claim_id in scene.claim_ids
        ) or '<span class="claim-chip neutral">editorial</span>'
        screen_text = "".join(
            f"<li>{_escape(line)}</li>" for line in scene.on_screen_text
        )
        scene_html.append(
            f"""
            <article class="scene">
              <div class="scene-index">{index:02d}</div>
              <div class="scene-main">
                <div class="scene-meta">{starts_at // 60}:{starts_at % 60:02d} · {scene.duration_seconds}s</div>
                <h3>{_escape(scene.scene_id.replace('_', ' ').title())}</h3>
                <p class="narration">{_escape(scene.narration)}</p>
                <div class="visual"><strong>Visual:</strong> {_escape(scene.visual_direction)}</div>
                <ul class="screen-text">{screen_text}</ul>
                <div class="claims">{claim_badges}</div>
              </div>
            </article>
            """
        )

    claim_rows = []
    for claim_id in sorted(claim_ids_used):
        claim = claims[claim_id]
        freshness = "RECHECK" if claim.get("freshness_check_required") else "STABLE"
        claim_rows.append(
            f"""
            <tr>
              <td><code>{_escape(claim_id)}</code></td>
              <td>{_escape(claim.get('statement', ''))}</td>
              <td>{_escape(claim.get('verification_state', ''))}</td>
              <td><span class="freshness {_escape(freshness.lower())}">{freshness}</span></td>
            </tr>
            """
        )

    source_cards = []
    for source in sources:
        safe_uri = _safe_link(source.uri)
        title = _escape(source.title or source.source_id)
        title_markup = (
            f'<a href="{_escape(safe_uri)}" rel="noreferrer">{title}</a>'
            if safe_uri
            else title
        )
        source_cards.append(
            f"""
            <article class="source-card">
              <code>{_escape(source.source_id)}</code>
              <h3>{title_markup}</h3>
              <p>{_escape(source.publisher or 'Publisher not recorded')}</p>
              <small>{_escape(source.notes or '')}</small>
            </article>
            """
        )

    notes = "".join(f"<li>{_escape(note)}</li>" for note in script.editorial_notes)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(script.working_title)} · Founder Review</title>
  <style>
    :root {{ --ink:#17212b; --paper:#f4efe3; --red:#e34a33; --blue:#1d4ed8; --line:#c9c0ae; --soft:#fffaf0; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:var(--paper); font-family:"Iowan Old Style","Palatino Linotype",Palatino,serif; }}
    body::before {{ content:""; position:fixed; inset:0; pointer-events:none; opacity:.22; background-image:linear-gradient(90deg,transparent 49%,rgba(23,33,43,.08) 50%,transparent 51%),linear-gradient(transparent 49%,rgba(23,33,43,.06) 50%,transparent 51%); background-size:38px 38px; }}
    main {{ position:relative; width:min(1180px,calc(100% - 32px)); margin:24px auto 80px; }}
    header {{ background:var(--ink); color:white; padding:clamp(28px,6vw,72px); border-radius:2px; box-shadow:12px 12px 0 var(--red); }}
    .eyebrow,.scene-meta,code,.status {{ font-family:"Avenir Next Condensed","Franklin Gothic Medium",sans-serif; letter-spacing:.08em; text-transform:uppercase; }}
    h1 {{ margin:.25em 0; max-width:900px; font-size:clamp(2.3rem,6vw,5.8rem); line-height:.94; font-weight:600; }}
    .status {{ display:inline-block; padding:8px 12px; background:var(--red); color:white; font-weight:800; }}
    .lede {{ max-width:760px; font-size:1.2rem; line-height:1.55; }}
    section {{ margin-top:64px; }}
    h2 {{ font-size:clamp(1.8rem,4vw,3.6rem); margin:0 0 24px; border-bottom:3px solid var(--ink); padding-bottom:10px; }}
    .summary-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
    .metric {{ background:var(--soft); border:1px solid var(--line); padding:22px; }}
    .metric strong {{ display:block; font-size:2rem; }}
    .scene {{ display:grid; grid-template-columns:90px 1fr; border-top:1px solid var(--line); padding:26px 0; gap:20px; }}
    .scene-index {{ font:700 3rem/1 "Avenir Next Condensed",sans-serif; color:var(--red); }}
    .scene h3 {{ font-size:1.7rem; margin:.2rem 0 .8rem; }}
    .narration {{ white-space:pre-line; font-size:1.08rem; line-height:1.7; max-width:850px; }}
    .visual {{ background:#dbe7ff; border-left:5px solid var(--blue); padding:14px 18px; margin:18px 0; line-height:1.5; }}
    .screen-text {{ display:flex; flex-wrap:wrap; list-style:none; padding:0; gap:8px; }}
    .screen-text li,.claim-chip {{ background:var(--ink); color:white; padding:6px 9px; font:700 .72rem/1.2 "Avenir Next Condensed",sans-serif; letter-spacing:.04em; }}
    .claim-chip {{ display:inline-block; margin:4px 5px 0 0; background:var(--blue); }}
    .claim-chip.neutral {{ background:#667085; }}
    table {{ width:100%; border-collapse:collapse; background:var(--soft); }}
    th,td {{ text-align:left; vertical-align:top; border:1px solid var(--line); padding:12px; line-height:1.45; }}
    th {{ background:var(--ink); color:white; }}
    .freshness {{ font:800 .7rem/1 sans-serif; padding:5px 7px; color:white; background:#238636; }}
    .freshness.recheck {{ background:var(--red); }}
    .source-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }}
    .source-card {{ background:var(--soft); border:1px solid var(--line); padding:20px; overflow-wrap:anywhere; }}
    .source-card h3 {{ margin:.7rem 0 .3rem; }}
    a {{ color:var(--blue); }}
    .approval {{ border:4px solid var(--red); background:#fff3ee; padding:24px; font-size:1.1rem; }}
    @media (max-width:760px) {{ .summary-grid,.source-grid {{ grid-template-columns:1fr; }} .scene {{ grid-template-columns:48px 1fr; }} .scene-index {{ font-size:2rem; }} table {{ display:block; overflow-x:auto; }} }}
  </style>
</head>
<body><main>
  <header>
    <div class="eyebrow">BS CATS · Founder Review Packet</div>
    <h1>{_escape(script.working_title)}</h1>
    <span class="status">Proposed · Not approved</span>
    <p class="lede">{_escape(script.description)}</p>
  </header>
  <section>
    <h2>Production brief</h2>
    <div class="summary-grid">
      <div class="metric"><strong>{script.target_duration_seconds // 60}:{script.target_duration_seconds % 60:02d}</strong>target runtime</div>
      <div class="metric"><strong>{len(script.scenes)}</strong>scenes</div>
      <div class="metric"><strong>{len(claim_ids_used)}</strong>linked claims</div>
    </div>
    <p><strong>Thumbnail:</strong> {_escape(script.thumbnail_text)}</p>
    <p><strong>Disclosure:</strong> {_escape(script.disclosure)}</p>
    <ul>{notes}</ul>
  </section>
  <section><h2>Script and shot plan</h2>{''.join(scene_html)}</section>
  <section><h2>Claim ledger</h2><table><thead><tr><th>ID</th><th>Claim</th><th>State</th><th>Freshness</th></tr></thead><tbody>{''.join(claim_rows)}</tbody></table></section>
  <section><h2>Source ledger</h2><div class="source-grid">{''.join(source_cards)}</div></section>
  <section class="approval"><strong>Human gate:</strong> verify every RECHECK item and confirm that the framing is fair. Rendering and distribution remain blocked until the script object is explicitly approved.</section>
</main></body></html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    os.chmod(output_path, 0o600)


def ingest_script(
    script: VideoScript,
    brief: UniversalObject,
    store: LocalObjectStore,
) -> UniversalObject:
    validate_script_against_brief(script, brief)
    item = UniversalObject(
        object_id=script.script_id,
        object_type="content_asset",
        title=script.working_title,
        purpose="Produce a source-linked video after explicit human approval.",
        created_by="script-agent",
        source=[source.uri for source in brief.sources],
        sources=brief.sources,
        tags=["video-script", "youtube", "human-review-required"],
        parent_ids=[brief.object_id],
        payload=script.model_dump(mode="json"),
        metadata={"asset_type": "video_script", "distribution_blocked": True},
    )
    captured = store.capture(item, actor_id="script-agent", actor_type=ActorType.agent)
    return store.curate(
        captured.object_id,
        CurationPatch(
            metadata={
                "content_stage": "ready_for_human_review",
                "human_review_required": True,
            }
        ),
        actor_id="script-agent",
        actor_type=ActorType.agent,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local founder review packet.")
    parser.add_argument("script", type=Path)
    parser.add_argument(
        "--store",
        type=Path,
        default=PROJECT_ROOT / ".local" / "object-events.jsonl",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ingest", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        script = VideoScript.model_validate_json(args.script.read_text(encoding="utf-8"))
        store = LocalObjectStore(args.store)
        brief = store.get(script.brief_object_id)
        if args.ingest:
            item = ingest_script(script, brief, store)
        else:
            validate_script_against_brief(script, brief)
            item = None
        output_path = args.output or (
            PROJECT_ROOT / ".local" / "reviews" / f"{script.script_id}.html"
        )
        render_review_packet(script, brief, output_path)
    except (OSError, ValidationError, ObjectStoreError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    result: dict[str, str | int] = {
        "script_id": script.script_id,
        "review_packet": str(output_path),
        "status": item.status.value if item else "validated",
    }
    if item:
        result["version"] = item.version
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
