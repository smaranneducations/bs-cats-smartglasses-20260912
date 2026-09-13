from copy import deepcopy
from types import SimpleNamespace
import unittest

from packages.intelligence.learning import (
    CreativeRule, LearningProposal, assert_memory_current, creative_settings,
    impact_report, retrieve_memory,
)
from packages.runtime.context import fingerprint


def item(identifier, kind, version=1, parents=(), payload=None, metadata=None, review="pending"):
    return SimpleNamespace(object_id=identifier, object_type=kind, version=version,
                           parent_ids=list(parents), payload=payload or {}, metadata=metadata or {},
                           status="captured", review=SimpleNamespace(state=review))


class MemoryStore:
    def __init__(self, objects):
        self.objects = objects

    def list_objects(self):
        return self.objects


class LearningMemoryTests(unittest.TestCase):
    def setUp(self):
        self.feedback = item("feedback_music", "feedback")
        self.proposal = LearningProposal(kind="scoped_preference", feedback_versions={"feedback_music": 1},
            workflow_families=["product"], proposed_rules=[{"key": "background_music_required", "value": True}],
            expected_benefit="Preserve the intended background-music experience.",
            evaluation="Music and narration must be assessed independently.", rollback="Retire the decision without weakening media-rights policy.")
        raw = self.proposal.model_dump(mode="json")
        self.decision = item("decision_music", "decision_record", parents=["feedback_music"],
            payload={"summary": "Music is independent of narration"},
            metadata={"intelligence_proposal": raw, "intelligence_proposal_hash": fingerprint(raw)})
        self.store = MemoryStore([self.feedback, self.decision])

    def test_pending_proposal_does_not_change_runtime_policy(self):
        memory = retrieve_memory(self.store, "product")
        self.assertEqual(memory["active_creative_rules"], {})
        self.assertEqual(memory["pending_relevant_proposals"], 1)

    def test_reviewed_fresh_scoped_proposal_is_retrieved(self):
        self.decision.review.state = "approved"
        memory = retrieve_memory(self.store, "product")
        self.assertEqual(memory["active_creative_rules"], {"background_music_required": True})
        self.assertEqual(memory["decisions"][0]["decision_id"], "decision_music")

    def test_workflow_scope_prevents_global_leakage(self):
        self.decision.review.state = "approved"
        self.assertEqual(retrieve_memory(self.store, "comparison")["decisions"], [])

    def test_updated_feedback_makes_previous_decision_stale(self):
        self.decision.review.state = "approved"
        self.feedback.version = 2
        memory = retrieve_memory(self.store, "product")
        self.assertEqual(memory["decisions"], [])
        self.assertEqual(memory["stale_decision_ids"], ["decision_music"])

    def test_context_revalidation_detects_review_changes(self):
        memory = retrieve_memory(self.store, "product")
        self.decision.review.state = "approved"
        with self.assertRaises(ValueError):
            assert_memory_current(self.store, memory)

    def test_tampered_proposal_does_not_enter_memory(self):
        self.decision.metadata["intelligence_proposal"]["expected_benefit"] = "Changed without updating its governed identity."
        with self.assertRaises(ValueError):
            retrieve_memory(self.store, "product")

    def test_feedback_cannot_grant_publishing_permission(self):
        with self.assertRaises(ValueError):
            CreativeRule(key="publication_allowed", value=True)

    def test_feedback_cannot_disable_required_music(self):
        with self.assertRaises(ValueError):
            CreativeRule(key="background_music_required", value=False)

    def test_creative_settings_preserve_nonnegotiable_boundaries(self):
        base = {"runtime_settings": {"duration_min_seconds": 60, "duration_max_seconds": 120,
            "background_music_required": True, "kinetic_text": True, "mechanical_narration_allowed": False,
            "media_rights_required": True, "voiceover_enabled": False}}
        values = creative_settings(base, {"active_creative_rules": {}})
        self.assertTrue(values["background_music_required"])
        self.assertFalse(values["voiceover_enabled"])

    def test_impact_traversal_follows_derived_outputs_without_changing_approval(self):
        product = item("product", "product")
        brief = item("brief", "content_brief", parents=["product"])
        storyboard = item("storyboard", "storyboard", parents=["brief"])
        orphan = item("legacy_asset", "content_asset")
        result = impact_report(MemoryStore([product, brief, storyboard, orphan]), ["product"])
        self.assertEqual([row["object_id"] for row in result["affected_objects"]], ["brief", "storyboard"])
        self.assertEqual(result["untracked_derived_objects"], ["legacy_asset"])
        self.assertFalse(result["approval_states_modified"])


if __name__ == "__main__":
    unittest.main()
