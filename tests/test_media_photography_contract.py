"""Photograph admission must not imply verified identity or publication rights."""
import unittest

from pydantic import ValidationError

from packages.contracts.media import MediaAssetPayload, RenderRecipePayload


class PhotographyContractTests(unittest.TestCase):
    def payload(self, **changes):
        data = {
            "summary": "Source-attributed fixture photograph, not a product test.",
            "asset_kind": "image",
            "asset_uri": "assets/media/commons/fixture/image.jpg",
            "sha256": "a" * 64,
            "provenance_kind": "open_license",
            "provenance_reference": "https://example.test/photo-license",
            "representation": "product_photography",
            "credit": "Fixture photographer; license receipt required.",
        }
        return data | changes

    def test_photographs_round_trip_without_becoming_illustrations(self):
        for representation in ("product_photography", "editorial_photography"):
            with self.subTest(representation=representation):
                asset = MediaAssetPayload.model_validate(self.payload(representation=representation))
                restored = MediaAssetPayload.model_validate_json(asset.model_dump_json())
                self.assertEqual(restored.representation, representation)

    def test_photo_admission_does_not_grant_rights_or_preview(self):
        asset = MediaAssetPayload.model_validate(self.payload())
        self.assertEqual(asset.rights_state, "unassessed")
        self.assertIsNone(asset.commercial_use_allowed)
        self.assertFalse(asset.private_preview_allowed)

    def test_documented_rights_are_preserved_not_inferred(self):
        asset = MediaAssetPayload.model_validate(self.payload(
            rights_state="documented", commercial_use_allowed=True))
        self.assertTrue(asset.commercial_use_allowed)
        self.assertFalse(asset.private_preview_allowed)

    def test_denied_rights_remain_denied(self):
        asset = MediaAssetPayload.model_validate(self.payload(
            rights_state="denied", commercial_use_allowed=False))
        self.assertEqual(asset.rights_state, "denied")
        self.assertFalse(asset.commercial_use_allowed)

    def test_non_image_assets_cannot_claim_photography(self):
        for kind in ("font", "procedural_audio"):
            for representation in ("product_photography", "editorial_photography"):
                with self.subTest(kind=kind, representation=representation):
                    with self.assertRaisesRegex(ValidationError, "requires an image"):
                        MediaAssetPayload.model_validate(self.payload(
                            asset_kind=kind, representation=representation))

    def test_generated_images_cannot_claim_photography(self):
        for representation in ("product_photography", "editorial_photography"):
            with self.subTest(representation=representation):
                with self.assertRaisesRegex(ValidationError, "cannot be represented as photography"):
                    MediaAssetPayload.model_validate(self.payload(
                        provenance_kind="generated_recipe", representation=representation))

    def test_existing_representations_remain_compatible(self):
        for kind, representation, provenance in (
            ("image", "concept_illustration", "legacy_workspace"),
            ("image", "concept_illustration", "generated_recipe"),
            ("font", "typography", "open_license"),
            ("procedural_audio", "original_synthesis", "generated_recipe"),
        ):
            with self.subTest(representation=representation, provenance=provenance):
                MediaAssetPayload.model_validate(self.payload(
                    asset_kind=kind, representation=representation,
                    provenance_kind=provenance))

    def test_recipe_schema_exposes_photography_without_publication_permission(self):
        schema = RenderRecipePayload.model_json_schema()
        options = schema["$defs"]["MediaAssetPayload"]["properties"]["representation"]["enum"]
        self.assertIn("product_photography", options)
        self.assertIn("editorial_photography", options)
        self.assertIs(schema["properties"]["publication_allowed"]["const"], False)
