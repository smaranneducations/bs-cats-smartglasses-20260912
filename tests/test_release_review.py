import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from packages.media.release_review import assess_release, canonical_hash, observe_render_file

NOW = datetime(2026, 9, 13, 5, 0, tzinfo=timezone.utc)


class Record:
    def __init__(self, value):
        self.value = value
        self.version = value["version"]

    def model_dump(self, **kwargs):
        return copy.deepcopy(self.value)


class Store:
    def __init__(self, records):
        self.records = records

    def get(self, identifier):
        return Record(self.records[identifier])

    def list_objects(self, object_type=None):
        return [Record(record) for record in self.records.values() if record["object_type"] == object_type]


class ReleaseReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.folder = self.root / ".local/production-renders/test"
        self.folder.mkdir(parents=True)
        (self.folder / "draft.mp4").write_bytes(b"bounded video fixture, not real encoded media")
        (self.folder / "soundtrack.wav").write_bytes(b"bounded audio fixture")
        source = {"source_id": "source_product", "uri": "https://manufacturer.example/product", "captured_at": NOW.isoformat()}
        media = {"rights_state": "documented", "commercial_use_allowed": True, "provenance_reference": "Fixture license reference", "credit": "Fixture credit"}
        recipe = {"input_versions": {"product_test": 1, "media_test": 1}, "assets": {"media_test": media}, "beats": [{"cells": [{"source_ids": ["source_product"]}]}]}
        metadata = {"title": "Fixture video", "description": "Fixture description", "visibility": "not_uploaded", "publication_allowed": False}
        video_hash = hashlib.sha256((self.folder / "draft.mp4").read_bytes()).hexdigest()
        manifest = {"schema_version": "render-manifest-1", "recipe": recipe, "recipe_object_id": "recipe_test", "recipe_version": 1, "recipe_sha256": canonical_hash(recipe), "video_sha256": video_hash, "publish_metadata": metadata, "metadata_sha256": canonical_hash(metadata), "soundtrack_sha256": hashlib.sha256((self.folder / "soundtrack.wav").read_bytes()).hexdigest()}
        (self.folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.records = {
            "render_test": {"object_id": "render_test", "object_type": "render_artifact", "version": 1, "status": "captured", "review": {"state": "pending"}, "sources": [source], "payload": {"summary": "Fixture artifact", "recipe_object_id": "recipe_test", "recipe_version": 1, "artifact_uri": ".local/production-renders/test/draft.mp4", "poster_uri": ".local/production-renders/test/poster.png", "manifest_uri": ".local/production-renders/test/manifest.json", "video_sha256": video_hash, "manifest_sha256": hashlib.sha256((self.folder / "manifest.json").read_bytes()).hexdigest(), "metadata_sha256": canonical_hash(metadata), "publish_metadata": metadata, "duration_seconds": 90.0, "width": 1280, "height": 720, "audio_present": True}},
            "recipe_test": {"object_id": "recipe_test", "object_type": "render_recipe", "version": 1, "payload": recipe},
            "product_test": {"object_id": "product_test", "object_type": "product", "version": 1, "status": "active", "review": {"state": "approved"}, "payload": {}},
            "media_test": {"object_id": "media_test", "object_type": "media_asset", "version": 1, "review": {"state": "approved"}, "payload": media},
            "policy_test": {"object_id": "policy_test", "object_type": "source_policy", "version": 1, "status": "active", "review": {"state": "approved"}, "updated_at": NOW.isoformat(), "payload": {"source_uri": source["uri"], "commercial_reuse": "allowed", "last_observed_at": NOW.isoformat(), "permission_expires_at": None, "refresh_days": 30}},
        }
        self.inspection = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720}, {"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "90.000000"}}

    def tearDown(self):
        self.temporary.cleanup()

    def packet(self, **kwargs):
        return assess_release(Store(self.records), "render_test", root=self.root, now=NOW, admission=kwargs.get("admission", lambda *_: None), prober=lambda _: self.inspection)["packet"]

    def state(self, identifier, **kwargs):
        return next(item["state"] for item in self.packet(**kwargs)["checks"] if item["check_id"] == identifier)

    def test_complete_prerequisites_still_require_human_and_grant_no_permission(self):
        result = self.packet()
        self.assertTrue(result["prerequisites_satisfied"])
        self.assertFalse(result["permission_granted"])
        self.assertFalse(result["cloud_and_spend_admission_assessed"])
        self.assertEqual(self.state("human_artifact_review"), "needs_review")

    def test_modified_video_is_blocked(self):
        (self.folder / "draft.mp4").write_bytes(b"different bytes")
        self.assertEqual(self.state("video_integrity"), "blocked")

    def test_modified_manifest_is_blocked(self):
        (self.folder / "manifest.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.state("manifest_integrity"), "blocked")

    def test_metadata_change_cannot_reuse_old_hash(self):
        self.records["render_test"]["payload"]["publish_metadata"]["title"] = "Unapproved new title"
        self.assertEqual(self.state("metadata_integrity"), "blocked")

    def test_missing_audio_is_blocked(self):
        (self.folder / "soundtrack.wav").unlink()
        self.assertEqual(self.state("soundtrack_integrity"), "blocked")

    def test_preview_resolution_is_not_final_delivery(self):
        self.records["render_test"]["payload"].update({"width": 768, "height": 432})
        self.assertEqual(self.state("delivery_resolution"), "needs_review")

    def test_changed_input_version_blocks_recipe(self):
        self.records["product_test"]["version"] = 2
        self.assertEqual(self.state("recipe_current"), "blocked")

    def test_existing_admission_failure_is_not_bypassed(self):
        def denied(*args):
            raise ValueError("Fixture admission failure")
        self.assertEqual(self.state("recipe_current", admission=denied), "blocked")

    def test_unreviewed_product_keeps_factual_review_open(self):
        self.records["product_test"]["review"]["state"] = "pending"
        self.assertEqual(self.state("factual_review"), "needs_review")

    def test_media_rights_denial_blocks_even_with_other_checks_passing(self):
        self.records["media_test"]["payload"]["commercial_use_allowed"] = False
        self.assertEqual(self.state("media_rights"), "blocked")

    def test_source_policy_at_exact_refresh_boundary_is_not_current(self):
        self.records["policy_test"]["payload"]["last_observed_at"] = (NOW - timedelta(days=30)).isoformat()
        self.assertEqual(self.state("source_policy"), "needs_review")

    def test_source_policy_expired_permission_is_not_current(self):
        self.records["policy_test"]["payload"]["permission_expires_at"] = NOW.isoformat()
        self.assertEqual(self.state("source_policy"), "needs_review")

    def test_file_outside_render_root_is_not_read(self):
        (self.root / "secret.txt").write_text("fixture must not be read", encoding="utf-8")
        result = observe_render_file(self.root, "secret.txt", ".txt", 1024)
        self.assertIsNone(result.sha256)
        self.assertIsNone(result.content)

    def test_oversized_file_is_not_read(self):
        result = observe_render_file(self.root, ".local/production-renders/test/draft.mp4", ".mp4", 2)
        self.assertIsNone(result.sha256)


if __name__ == "__main__":
    unittest.main()
