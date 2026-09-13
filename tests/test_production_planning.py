from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from packages.contracts.governance import SourcePolicyPayload
from packages.contracts.object import UniversalObject
from packages.contracts.production import StoryboardPayload, build_storyboard, refresh_job, source_refresh_plan
from packages.contracts.store import ContractViolationError, ObjectNotFoundError
from services.api.src.workspace_planning import planning_router
from scripts.render_storyboard_video import animated_frame, current_bundle, plates


NOW = datetime(2026, 9, 13, tzinfo=UTC)


def fixture_brief(family="comparison"):
    claims = []
    inputs = {}
    groups = []
    for product in ["fixture_a", "fixture_b"]:
        ids = []
        for key, value in [("weight_g", "80 g"), ("fov_deg", "40 degrees"), ("refresh_hz", "90 Hz")]:
            cid = product + "_" + key
            ids.append(cid)
            claims.append({"claim_id": cid, "statement": f"Manufacturer states for {product}: {key} = {value}.",
                           "caveats": ["Fixture data only. Not independently tested."]})
            inputs[cid] = {"object_id": product, "field_key": key}
        groups.append({"claim_ids": ids})
    return UniversalObject(object_id="fixture_brief", object_type="content_brief",
        title="Fixture comparison", purpose="Synthetic local test data.",
        payload={"summary": "A fixture, not a product recommendation.", "workflow_family": family,
                 "input_versions": {"fixture_a": 1, "fixture_b": 1}, "entities": ["fixture_a", "fixture_b"],
                 "duration_seconds": 90, "claims": claims,
                 "presentation": {"hook": "What differs in this fixture?", "sections": groups}},
        metadata={"claim_inputs": inputs})


def fixture_policy():
    return UniversalObject(object_id="fixture_policy", object_type="source_policy",
        title="Fixture source policy", purpose="Synthetic permission tests.",
        payload={"summary": "Fixture only.", "source_uri": "https://example.com/data",
                 "publisher": "Example", "access": "api", "automation": "pending",
                 "commercial_reuse": "pending", "media_reuse": "pending",
                 "rights_basis": "None recorded.", "attribution": "Example",
                 "refresh_days": 7, "last_observed_at": NOW.isoformat()})


class MemoryStore:
    def __init__(self, objects):
        self.objects = {item.object_id: item for item in objects}
        self.captures = 0

    def get(self, oid):
        if oid not in self.objects:
            raise ObjectNotFoundError(oid)
        return self.objects[oid]

    def list_objects(self, object_type=None):
        return [item for item in self.objects.values() if item.object_type == object_type]

    def capture(self, item, **kwargs):
        self.objects[item.object_id] = item
        self.captures += 1
        return item


class ProductionPlanningTests(unittest.TestCase):
    def test_comparison_preserves_matched_claims_and_exact_duration(self):
        brief = fixture_brief()
        result = build_storyboard(brief)
        plan = StoryboardPayload.model_validate(result.payload)
        comparisons = [scene for scene in plan.scenes if scene.primitive == "comparison_table"]
        self.assertEqual(len(comparisons), 1)
        self.assertTrue(all(len(scene.claim_ids) == 2 for scene in comparisons))
        self.assertEqual(sum(scene.duration_seconds for scene in plan.scenes), 90)
        self.assertFalse(plan.publication_allowed)
        self.assertEqual(plan.narration, "none")
        self.assertEqual([scene.story_role for scene in plan.scenes],
                         ["hook", "tension", "differentiator_and_proof", "implication", "payoff"])
        self.assertLessEqual(plan.scenes[0].duration_seconds, 8)
        self.assertEqual(len(plan.story_strategy.evidence_anchor_claim_ids), 2)
        self.assertEqual(plan.creative_gate.strong_model_review_state, "required_before_release_candidate")

    def test_storyboard_identity_is_stable_and_revision_sensitive(self):
        brief = fixture_brief()
        self.assertEqual(build_storyboard(brief).object_id, build_storyboard(brief).object_id)
        newer = brief.model_copy(update={"version": 2})
        self.assertNotEqual(build_storyboard(brief).object_id, build_storyboard(newer).object_id)
        self.assertEqual(build_storyboard(brief).object_id, build_storyboard(brief, "9:16").object_id)
        with self.assertRaises(ContractViolationError):
            build_storyboard(brief, "16:9")

    def test_invalid_timing_duplicate_scene_and_publish_flag_are_rejected(self):
        original = build_storyboard(fixture_brief()).payload
        for key in ["duration", "duplicate", "publish", "arc", "evidence_anchor", "creative_gate"]:
            data = deepcopy(original)
            if key == "duration":
                data["scenes"][0]["duration_seconds"] += 1
            elif key == "duplicate":
                data["scenes"][1]["scene_id"] = data["scenes"][0]["scene_id"]
            else:
                if key == "publish":
                    data["publication_allowed"] = True
                elif key == "arc":
                    data["scenes"][1]["story_role"] = "hook"
                elif key == "evidence_anchor":
                    data["story_strategy"]["evidence_anchor_claim_ids"] = ["missing_claim"]
                else:
                    data["creative_gate"]["decision_lever_source_bound"] = False
            with self.subTest(case=key), self.assertRaises(ValidationError):
                StoryboardPayload.model_validate(data)

    def test_commercial_workflow_and_unreadable_claim_are_rejected(self):
        with self.assertRaises(ContractViolationError):
            build_storyboard(fixture_brief("commercial"))
        brief = fixture_brief("product")
        brief.payload["claims"][0]["statement"] = "x" * 241
        with self.assertRaises(ContractViolationError):
            build_storyboard(brief)

    def test_pending_policy_reports_separate_blockers_without_execution(self):
        plan = source_refresh_plan(fixture_policy(), NOW)
        self.assertFalse(plan["due"])
        self.assertFalse(plan["execution_enabled"])
        self.assertGreaterEqual(len(plan["blockers"]), 5)

    def test_even_approved_permissions_cannot_activate_disconnected_collector(self):
        policy = fixture_policy()
        policy.status = "active"
        # model construction supplies enum conversion rather than mutating it.
        policy = UniversalObject.model_validate(policy.model_dump() | {
            "status": "active", "review": {"state": "approved", "reviewed_by": "fixture",
                                         "reviewed_at": NOW.isoformat()},
            "payload": policy.payload | {"automation": "allowed", "commercial_reuse": "allowed",
                "terms_uri": "https://example.com/terms", "permission_expires_at": (NOW + timedelta(days=2)).isoformat()}
        })
        plan = source_refresh_plan(policy, NOW)
        self.assertEqual(len(plan["blockers"]), 1)
        self.assertFalse(plan["execution_enabled"])

    def test_permission_expiry_is_required_and_must_have_timezone(self):
        data = fixture_policy().payload | {"automation": "allowed", "terms_uri": "https://example.com/terms"}
        for expiry in [None, "2026-09-20T00:00:00"]:
            with self.subTest(expiry=expiry), self.assertRaises(ValidationError):
                SourcePolicyPayload.model_validate(data | {"permission_expires_at": expiry})
        SourcePolicyPayload.model_validate(data | {"permission_expires_at": "2026-09-20T00:00:00Z"})

    def test_refresh_identity_uses_policy_version_not_wall_clock(self):
        policy = fixture_policy()
        self.assertEqual(refresh_job(policy, NOW).object_id, refresh_job(policy, NOW + timedelta(hours=1)).object_id)
        self.assertNotEqual(refresh_job(policy, NOW).object_id,
                            refresh_job(policy.model_copy(update={"version": 2}), NOW).object_id)

    def test_expired_permission_is_a_distinct_blocker(self):
        policy = fixture_policy()
        policy.payload["permission_expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
        self.assertIn("Source permission review has expired.", source_refresh_plan(policy, NOW)["blockers"])

    def test_planning_api_replay_and_revision_conflict(self):
        store = MemoryStore([fixture_brief(), fixture_policy()])
        actor = SimpleNamespace(actor_id="fixture-agent", actor_type="agent")
        app = FastAPI()
        app.include_router(planning_router(lambda: store, lambda: actor, lambda: actor))
        with TestClient(app) as client:
            self.assertFalse(client.get("/v1/sources/refresh-plan").json()["execution_enabled"])
            body = {"brief_object_id": "fixture_brief", "expected_version": 1}
            first = client.post("/v1/content/storyboards", json=body)
            second = client.post("/v1/content/storyboards", json=body)
            self.assertEqual(first.status_code, 201)
            self.assertEqual(first.json()["object_id"], second.json()["object_id"])
            self.assertEqual(store.captures, 1)
            self.assertEqual(client.post("/v1/content/storyboards", json=body | {"expected_version": 2}).status_code, 409)

    def test_planning_writes_use_editor_dependency(self):
        actor = SimpleNamespace(actor_id="reader", actor_type="system")
        def deny():
            raise HTTPException(403, "Read-only fixture.")
        app = FastAPI()
        app.include_router(planning_router(lambda: MemoryStore([]), lambda: actor, deny))
        with TestClient(app) as client:
            self.assertEqual(client.post("/v1/sources/refresh-plan").status_code, 403)
            self.assertEqual(client.post("/v1/content/storyboards",
                json={"brief_object_id": "fixture_brief", "expected_version": 1}).status_code, 403)

    def test_export_layout_and_animation_for_both_aspects(self):
        plan = StoryboardPayload.model_validate(build_storyboard(fixture_brief()).payload)
        for aspect, size in [("16:9", (768, 432)), ("9:16", (432, 768))]:
            for index, scene in enumerate(plan.scenes):
                base, layer = plates(scene, index, len(plan.scenes), aspect)
                self.assertEqual(base.size, size)
                frame = animated_frame(base, layer, 1, scene.duration_seconds)
                self.assertEqual(frame.mode, "RGB")
                self.assertNotEqual(frame.tobytes(), base.tobytes())

    def test_export_rejects_stale_or_reworded_factual_inputs(self):
        brief = fixture_brief()
        storyboard = build_storyboard(brief)
        products = [UniversalObject(object_id=oid, object_type="product", title=oid, purpose="Fixture")
                    for oid in brief.payload["input_versions"]]
        store = MemoryStore([brief, storyboard] + products)
        current_bundle(store, storyboard.object_id)
        store.objects["fixture_a"] = products[0].model_copy(update={"version": 2})
        with self.assertRaises(ValueError):
            current_bundle(store, storyboard.object_id)
        store.objects["fixture_a"] = products[0]
        storyboard.payload["scenes"][2]["lines"][0] = "An unsupported rewritten claim."
        with self.assertRaises(ValueError):
            current_bundle(store, storyboard.object_id)


if __name__ == "__main__":
    unittest.main()
