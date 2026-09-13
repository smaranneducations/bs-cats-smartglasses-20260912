#!/usr/bin/env python3
"""Capture sanitized feedback and prepare decisions without approving them."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts.object import ActorType, UniversalObject
from packages.intelligence.learning import LearningProposal, prepare_decision
from services.api.src.main import get_store


def main():
    store = get_store()
    existing = {item.object_id: item for item in store.list_objects()}
    additions = [
        ("feedback_background_music_20260913", "Background music is independent of narration", "preference",
         "The human clarified that audio means background music. The original 60-120 second preference was superseded by a 30-90 second 9:16 canonical format, without mechanical narration.",
         "Keep background music, voiceover and media-rights requirements as separate typed creative settings."),
        ("feedback_engineering_quality_20260913", "Resolve root causes and complete the real architecture", "operating_directive",
         "The human asked for root-cause repairs rather than design bypasses, placeholders or a permanent technical backlog. Intelligence should improve actual outcomes, not just architectural complexity.",
         "Distinguish specified, authored, executed, validated and deployed states; finish the required end-to-end workflow."),
    ]
    for object_id, summary, classification, intent, improvement in additions:
        if object_id not in existing:
            item = UniversalObject(object_id=object_id, object_type="feedback", title=summary,
                purpose="Retain scoped, sanitized human intent as a governed feedback object.",
                payload={"summary": summary, "input": intent, "classification": classification,
                         "target_ids": [], "proposed_improvement": improvement},
                metadata={"source_basis": "Explicit project conversation, summarized without credentials or raw chat.",
                          "capture_actor": "agent", "product_fact": False})
            store.capture(item, actor_id="agent:intelligence-learning", actor_type=ActorType.agent,
                          idempotency_key="capture-" + object_id,
                          request_input={"intent": intent, "improvement": improvement})
    results = []
    for feedback in store.list_objects():
        if feedback.object_type != "feedback":
            continue
        music = feedback.object_id == "feedback_background_music_20260913"
        proposal = LearningProposal(
            kind="scoped_preference" if music else "evaluation_case",
            workflow_families=sorted(["category", "product", "feature", "comparison", "use_case", "value", "change", "compatibility", "question", "myth", "market", "commercial"]) if music else [],
            feedback_versions={feedback.object_id: feedback.version},
            target_ids=feedback.payload.get("target_ids", []),
            proposed_rules=[{"key": "background_music_required", "value": True}, {"key": "voiceover_enabled", "value": False}] if music else [],
            expected_benefit=feedback.payload.get("proposed_improvement") or "Reduce repeated human explanation and make the resulting decision observable.",
            evaluation="For an audience-facing video, independently check background music, no mechanical narration, permitted imagery and the current 30-90 second 9:16 range." if music else "At the next relevant workflow, show the feedback disposition, evidence boundaries and the observable outcome; do not treat the feedback as a verified product fact.",
            rollback="Retire or supersede this scoped decision if its evaluation regresses; preserve its lineage and do not alter reserved permissions.")
        decision = prepare_decision(store, feedback.object_id, proposal)
        results.append({"feedback_id": feedback.object_id, "decision_id": decision.object_id,
                        "review_state": decision.review.state.value})
    print(json.dumps({"decisions": results, "human_approvals_written": 0, "provider_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
