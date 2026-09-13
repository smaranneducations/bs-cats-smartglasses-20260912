from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from PIL import Image

from packages.contracts.governance import BASE_FIELD_MAP
from packages.contracts.media import ImageBeat, MediaAssetPayload, RenderCell
from packages.contracts.object import SourceReference, UniversalObject
from packages.contracts.workflows import PRIMITIVES, compose_brief
from packages.media.planning import validate_storyboard
from packages.media.renderer import frame_for, glyph, prepare_layers
from packages.runtime.context import ROOT


class FixtureStore:
    def __init__(self, objects):
        self.objects = objects

    def list_objects(self):
        return self.objects

    def definitions(self):
        return BASE_FIELD_MAP


class GovernedMediaTests(unittest.TestCase):
    def setUp(self):
        self.display = ROOT / "assets/fonts/barlow-condensed/BarlowCondensed-ExtraBold.ttf"
        self.body = ROOT / "assets/fonts/barlow-condensed/BarlowCondensed-Medium.ttf"
        source = SourceReference(source_id="source_specs",uri="https://example.test/specifications",title="Fixture manufacturer specifications",publisher="Fixture",captured_at=datetime(2026,9,13,tzinfo=timezone.utc))
        products = [UniversalObject(object_id="product_"+key,object_type="product",title="Product "+key,purpose="Source-bound media fixture.",sources=[source],
            payload={"brand":"Fixture","category":"display","market":"Explicit fixture market","variant":key,"buyer_job":"A compatible private display","summary":"Fixture record, not a real recommendation.",
                     "fields":{"weight_g":{"value":weight,"source_ids":["source_specs"],"evidence_kind":"manufacturer_stated","conditions":"Stated mass, not comfort.","observed_at":"2026-09-13T00:00:00Z","confidence":None}},"caveats":[]}) for key,weight in (("a",87),("b",82))]
        brief = compose_brief("comparison",products,"test-agent","test-media-brief",BASE_FIELD_MAP)
        claims = brief.payload["claims"]
        story = UniversalObject(object_id="storyboard_fixture",object_type="storyboard",title="Source-linked fixture",purpose="Keep source claims unchanged.",parent_ids=[brief.object_id],
            payload={"brief_object_id":brief.object_id,"brief_version":brief.version,"workflow_family":"comparison",
                     "scenes":[{"claim_ids":[claim["claim_id"] for claim in claims],"lines":[claim["statement"] for claim in claims]}]})
        self.products,self.brief,self.story = products,brief,story
        self.store = FixtureStore([*products,brief,story])

    def beat(self, primitive="question_hook"):
        cells = [RenderCell(claim_id="claim_"+key,object_id="product_"+key,product_title="Product "+key,concept_key="weight_g",concept_label="Stated weight",value_display=value,source_statement="Manufacturer-stated fixture weight.",source_ids=["source_specs"]) for key,value in (("a","87 g"),("b","82 g"))]
        return ImageBeat(beat_id="beat_fixture",source_scene_id="scene_fixture",primitive=primitive,heading="Compare the right thing",lines=["A useful question, not an automatic winner."],claim_cells=cells if primitive=="comparison_table" else [],duration_seconds=6,image_asset_id="image_fixture",accent="orange")

    def test_current_exact_claims_are_admitted(self):
        result = validate_storyboard(self.store,self.story.object_id)
        self.assertEqual(result[0].object_id,self.story.object_id)

    def test_changed_source_version_blocks_rendering(self):
        self.products[0].version = 2
        with self.assertRaises(ValueError):
            validate_storyboard(self.store,self.story.object_id)

    def test_edited_factual_line_is_not_silently_rendered(self):
        self.story.payload["scenes"][0]["lines"][0] = "An invented winning product."
        with self.assertRaises(ValueError):
            validate_storyboard(self.store,self.story.object_id)

    def test_missing_claim_binding_is_rejected(self):
        self.story.payload["scenes"][0]["claim_ids"] = ["unavailable_claim"]
        self.story.payload["scenes"][0]["lines"] = ["An unsupported claim."]
        with self.assertRaises(ValueError):
            validate_storyboard(self.store,self.story.object_id)

    def test_all_twelve_primitives_build_landscape_and_portrait_layers(self):
        self.assertEqual(len(PRIMITIVES),12)
        for primitive in PRIMITIVES:
            for width,height in ((768,432),(432,768)):
                with self.subTest(primitive=primitive,size=(width,height)):
                    layers = prepare_layers(self.beat(primitive),width,height,self.display,self.body)
                    self.assertGreaterEqual(len(layers),2)
                    for layer in layers:
                        self.assertGreaterEqual(layer.x,0)
                        self.assertGreaterEqual(layer.y,0)
                        self.assertLessEqual(layer.x+layer.image.width,width)
                        self.assertLessEqual(layer.y+layer.image.height,height-5)

    def test_progress_bar_continues_after_text_has_settled(self):
        width,height = 768,432
        beat = self.beat()
        bg = Image.new("RGB",(width+80,height+46),"#224466")
        shade = Image.new("RGBA",(width,height))
        notice = Image.new("RGBA",(1,1))
        early = frame_for(beat,bg,[],shade,notice,width,height,3,0,90,0)
        late = frame_for(beat,bg,[],shade,notice,width,height,3,70,90,0)
        self.assertNotEqual(early.getpixel((width//2,height-2)),late.getpixel((width//2,height-2)))

    def test_overflowing_copy_is_not_truncated(self):
        with self.assertRaises(ValueError):
            glyph("Unbreakable"*100,self.display,30,30,20)

    def test_unassessed_media_is_not_implicitly_available(self):
        asset = MediaAssetPayload(summary="Fixture asset",asset_kind="image",asset_uri=".local/assets/kinetic/fixture.png",sha256="a"*64,
            provenance_kind="legacy_workspace",provenance_reference="Unresolved fixture provenance",representation="concept_illustration",credit="Fixture only")
        self.assertFalse(asset.private_preview_allowed)
        self.assertIsNone(asset.commercial_use_allowed)

    def test_out_of_bounds_image_crop_is_rejected(self):
        payload = self.beat().model_dump(mode="json")
        payload["crop"] = [0,0,1.1,1]
        with self.assertRaises(ValueError):
            ImageBeat.model_validate(payload)

    def test_comparison_requires_two_explicit_cells(self):
        payload = self.beat().model_dump(mode="json")
        payload["primitive"] = "comparison_table"
        with self.assertRaises(ValueError):
            ImageBeat.model_validate(payload)


if __name__ == "__main__":
    unittest.main()
