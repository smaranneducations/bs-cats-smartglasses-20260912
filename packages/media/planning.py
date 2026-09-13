from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from packages.contracts.media import ImageBeat, MediaAssetPayload, RenderCell, RenderRecipePayload
from packages.contracts.object import ActorType, UniversalObject
from packages.contracts.workflows import compose_brief, project_field_claim
from packages.knowledge.semantic import SemanticTools
from packages.intelligence.learning import assert_memory_current, creative_settings, retrieve_memory
from packages.media.catalog import register_file
from packages.runtime.context import ROOT, fingerprint, reject_obvious_credentials


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def capture_once(store, item, key):
    existing = {obj.object_id: obj for obj in store.list_objects()}
    if item.object_id in existing:
        return existing[item.object_id]
    return store.capture(item, actor_id="agent:media-planner", actor_type=ActorType.agent,
                         idempotency_key=key, request_input={"object_id": item.object_id, "payload": item.payload})


def register_assets(store):
    specifications = []
    for name in ("01-capture.png", "02-glance.png", "03-screen.png"):
        uri = ".local/assets/kinetic/" + name
        specifications.append(MediaAssetPayload(summary="Legacy preferred-style image, retained only for private creative review.",
            asset_kind="image", asset_uri=uri, sha256=file_hash(ROOT / uri), provenance_kind="legacy_workspace",
            provenance_reference="Existing kinetic prototype asset; an authoritative generation or license record has not been recovered.",
            representation="concept_illustration", private_preview_allowed=True,
            credit="Conceptual imagery, not verified product photography. Commercial media rights remain unassessed."))
    for name in ("BarlowCondensed-ExtraBold.ttf", "BarlowCondensed-Medium.ttf"):
        uri = "assets/fonts/barlow-condensed/" + name
        specifications.append(MediaAssetPayload(summary="Barlow Condensed font, distributed with its unmodified SIL OFL license.",
            asset_kind="font", asset_uri=uri, sha256=file_hash(ROOT / uri), provenance_kind="open_license",
            provenance_reference="https://github.com/google/fonts/tree/main/ofl/barlowcondensed",
            representation="typography", private_preview_allowed=True, rights_state="documented", commercial_use_allowed=True,
            credit="Copyright 2017 The Barlow Project Authors. SIL Open Font License 1.1; see the packaged OFL.txt."))
    specifications.append(MediaAssetPayload(summary="Procedural background soundtrack with no loaded third-party audio sample.",
        asset_kind="procedural_audio", asset_uri="scripts/render_kinetic_video.py",
        sha256=file_hash(ROOT / "scripts/render_kinetic_video.py"), provenance_kind="generated_recipe",
        provenance_reference="synthesize_soundtrack: deterministic oscillators and seeded noise; 120 BPM.",
        representation="original_synthesis", private_preview_allowed=True, rights_state="documented", commercial_use_allowed=True,
        credit="Original procedural project soundtrack; the recipe is pinned, and the generated audio receives its own output hash."))
    registered = {}
    for payload in specifications:
        if payload.asset_kind == "image":
            register_file(ROOT / payload.asset_uri, {
                "origin": payload.provenance_kind,
                "subject": "SmartGlasses conceptual context",
                "scene": "kinetic video background",
                "style": "realistic colorful technology lifestyle",
                "purpose": "private creative preview",
                "tags": ["smart_glasses", "technology", "kinetic_video", "background"],
                "rights_state": payload.rights_state,
                "commercial_use_allowed": payload.commercial_use_allowed,
                "source_uri": payload.provenance_reference,
                "representation": payload.representation,
                "not_product_photography": True,
                "depiction_limits": ["Do not identify the image as a named product or camera sample."],
                "cost_usd": 0.0,
            }, root=ROOT)
        identifier = "media_" + payload.sha256[:32]
        obj = UniversalObject(object_id=identifier, object_type="media_asset",
            title=Path(payload.asset_uri).name, purpose="Track source bytes, representation, permitted uses and review state for a reusable media primitive.",
            payload=payload.model_dump(mode="json"), metadata={"publication_allowed": False})
        registered[payload.asset_uri] = capture_once(store, obj, "media-" + payload.sha256)
    return registered


def current_objects(store):
    items = store.list_objects()
    if len(items) > 500:
        raise ValueError("Use a bounded object adapter before exceeding this working set.")
    return {item.object_id: item for item in items}


def validate_storyboard(store, storyboard_id):
    objects = current_objects(store)
    story = objects.get(storyboard_id)
    if story is None or story.object_type != "storyboard":
        raise ValueError("A governed storyboard is required.")
    data = story.payload
    brief = objects.get(data["brief_object_id"])
    if not brief or brief.object_type != "content_brief" or brief.version != data["brief_version"]:
        raise ValueError("The source brief changed; regenerate the storyboard.")
    products = []
    for identifier, version in brief.payload["input_versions"].items():
        product = objects.get(identifier)
        if not product or product.version != version:
            raise ValueError("A source object changed; revalidate the brief and storyboard.")
        products.append(product)
    definitions = store.definitions()
    # Retain workflow/category/retirement validation without using its editorial
    # first-six-field selection as the universe of admissible assertions.
    compose_brief(data["workflow_family"], products, "agent:render-validation", "render-validation-" + storyboard_id, definitions)
    stored = {claim["claim_id"]: claim for claim in brief.payload["claims"]}
    if len(stored) != len(brief.payload["claims"]) or not stored:
        raise ValueError("The brief requires distinct source-bound claims.")
    bindings = brief.metadata.get("claim_inputs", {})
    sources = {}
    for product in products:
        for source in product.sources:
            value = source.model_dump(mode="json")
            if source.source_id in sources and sources[source.source_id] != value:
                raise ValueError("Conflicting product source identities require review.")
            sources[source.source_id] = value
    brief_sources = {source.source_id: source.model_dump(mode="json") for source in brief.sources}
    semantic_cache = {}
    for claim_id, claim in stored.items():
        binding = bindings.get(claim_id, {})
        product_id, key = binding.get("object_id"), binding.get("field_key")
        if product_id not in brief.payload["input_versions"]:
            raise ValueError("A claim is not bound to a pinned product.")
        product = objects[product_id]
        expected, expected_binding = project_field_claim(product, key, definitions)
        if binding.get("definition") != expected_binding["definition"]:
            raise ValueError("A claim's ontology definition changed.")
        if binding.get("object_version", product.version) != product.version:
            raise ValueError("A claim's pinned product version changed.")
        try:
            observed = datetime.fromisoformat(str(binding.get("observed_at")).replace("Z", "+00:00"))
            current = datetime.fromisoformat(str(expected_binding["observed_at"]).replace("Z", "+00:00"))
            if observed.tzinfo is None or current.tzinfo is None or observed != current:
                raise ValueError("A claim's observation date changed.")
        except (TypeError, ValueError) as error:
            raise ValueError("A claim requires its current timezone-aware observation date.") from error
        if binding.get("evidence_kind") != expected_binding["evidence_kind"]:
            raise ValueError("A claim's evidence kind changed.")
        for field in ("statement", "kind", "evidence_tier", "verification_state", "confidence", "freshness_check_required"):
            if claim.get(field) != expected[field]:
                raise ValueError("A claim differs from its current governed assertion.")
        if set(claim.get("source_ids", [])) != set(expected["source_ids"]):
            raise ValueError("Claim source identity changed.")
        if any(brief_sources.get(source_id) != sources[source_id] for source_id in expected["source_ids"]):
            raise ValueError("A brief source reference differs from the pinned product source.")
        required_caveats = {text for text in expected["caveats"] if not text.startswith("Observation date: ")}
        if not required_caveats.issubset(set(claim.get("caveats", []))):
            raise ValueError("A claim omitted required evidence conditions or caveats.")
        if "assertion_id" in binding:
            if product_id not in semantic_cache:
                projected = SemanticTools(store).assertions(product_id)
                if projected["version"] != product.version:
                    raise ValueError("The semantic product version changed.")
                semantic_cache[product_id] = {row["concept_id"]: row for row in projected["assertions"]}
            row = semantic_cache[product_id].get("concept_" + key, {})
            for saved_key, projected_key in (
                ("assertion_id", "assertion_id"), ("definition_hash", "definition_hash"),
                ("semantic_source_ids", "source_ids"), ("semantic_evidence_ids", "evidence_ids"),
                ("semantic_conditions", "conditions"),
            ):
                if saved_key not in binding or binding[saved_key] != row.get(projected_key):
                    raise ValueError("A claim's semantic assertion lineage changed.")
    for scene in data["scenes"]:
        ids = scene["claim_ids"]
        if ids and len(ids) != len(scene["lines"]):
            raise ValueError("Claim lines must preserve one-to-one source bindings.")
        for claim_id, line in zip(ids, scene["lines"]):
            if claim_id not in stored:
                raise ValueError("An on-screen claim is unavailable in the current evidence projection.")
            if line != stored[claim_id]["statement"]:
                raise ValueError("An on-screen claim differs from its current governed assertion.")
    return story, brief, objects, definitions, stored


def prepare_recipe(store, storyboard_id):
    story, brief, objects, definitions, claims = validate_storyboard(store, storyboard_id)
    assets = register_assets(store)
    profile = json.loads((ROOT / "config/creative-direction.json").read_text())
    memory = retrieve_memory(store, story.payload["workflow_family"], list(brief.payload["input_versions"]))
    settings = creative_settings(profile, memory)
    image_choices = [
        (assets[".local/assets/kinetic/03-screen.png"].object_id, (0.0, 0.0, 1.0, 1.0)),
        (assets[".local/assets/kinetic/01-capture.png"].object_id, (0.0, 0.05, 0.52, 0.95)),
        (assets[".local/assets/kinetic/02-glance.png"].object_id, (0.55, 0.0, 1.0, 1.0)),
    ]
    beats = []
    for scene_index, scene in enumerate(story.payload["scenes"]):
        cells = []
        for claim_id in scene["claim_ids"]:
            binding = brief.metadata["claim_inputs"][claim_id]
            product, key = objects[binding["object_id"]], binding["field_key"]
            definition = definitions[key]
            if binding["definition"] != definition.model_dump(mode="json"):
                raise ValueError("A claim's ontology definition changed.")
            value = product.payload["fields"][key]["value"]
            display = str(value).lower() if isinstance(value, bool) else str(value)
            cells.append(RenderCell(claim_id=claim_id, object_id=product.object_id, product_title=product.title,
                concept_key=key, concept_label=definition.label,
                value_display=display + (" " + definition.unit if definition.unit else ""),
                source_statement=claims[claim_id]["statement"], source_ids=claims[claim_id]["source_ids"]))
        duration = float(scene["duration_seconds"])
        if scene["primitive"] == "comparison_table":
            if len(cells) != 2 or cells[0].concept_key != cells[1].concept_key:
                raise ValueError("Comparison graphics require two matched concept cells.")
            first, middle = duration * 0.28, duration * 0.44
            parts = [
                ("question_reveal", [cells[0].concept_label], [], first),
                ("comparison_table", [cells[0].concept_label], cells, middle),
                ("evidence_note", [scene["notes"][0] if scene["notes"] else "Manufacturer statements are not hands-on tests."], [], duration-first-middle),
            ]
        else:
            lines = scene["lines"]
            if duration > 12 or len(lines) > 1:
                left = max(1, len(lines) // 2)
                parts = [(scene["primitive"], lines[:left], cells[:left], duration / 2),
                         (scene["primitive"], lines[left:] or lines[:left], cells[left:], duration / 2)]
            else:
                parts = [(scene["primitive"], lines, cells, duration)]
        for part_index, (primitive, lines, visible_cells, seconds) in enumerate(parts):
            image_id, crop = image_choices[(scene_index + part_index) % len(image_choices)]
            beats.append(ImageBeat(beat_id=f"{scene['scene_id']}_beat_{part_index+1}", source_scene_id=scene["scene_id"],
                primitive=primitive, heading=scene["heading"], lines=lines, notes=scene["notes"], claim_cells=visible_cells,
                duration_seconds=seconds, image_asset_id=image_id, crop=crop,
                accent=("orange", "mint", "cyan", "amber")[(scene_index + part_index) % 4]))
    versions = {story.object_id: story.version, brief.object_id: brief.version, **brief.payload["input_versions"],
                **{asset.object_id: asset.version for asset in assets.values()},
                **{entry["decision_id"]: entry["decision_version"] for entry in memory["decisions"]}}
    payload = RenderRecipePayload(summary="Image-led adaptation of a source-bound storyboard for private human review.",
        storyboard_object_id=story.object_id, storyboard_version=story.version, workflow_family=story.payload["workflow_family"],
        aspect_ratio=story.payload["aspect_ratio"], duration_seconds=story.payload["duration_seconds"],
        creative_profile_revision=profile["revision"], creative_profile_sha256=fingerprint(profile),
        ontology_sha256=fingerprint({key: value.model_dump(mode="json") for key, value in definitions.items()}),
        renderer_sha256=file_hash(ROOT / "packages/media/renderer.py"), input_versions=versions,
        creative_settings=settings, governed_memory=memory,
        assets={asset.object_id: MediaAssetPayload.model_validate(asset.payload) for asset in assets.values()}, beats=beats,
        soundtrack_asset_id=assets["scripts/render_kinetic_video.py"].object_id,
        display_font_asset_id=assets["assets/fonts/barlow-condensed/BarlowCondensed-ExtraBold.ttf"].object_id,
        body_font_asset_id=assets["assets/fonts/barlow-condensed/BarlowCondensed-Medium.ttf"].object_id,
        adaptation_reason="Apply the current image/music creative profile to the earlier abstract-only technical storyboard without changing its factual assertions or granting publication permission.")
    reject_obvious_credentials(payload.model_dump(mode="json"))
    key = fingerprint(payload.model_dump(mode="json"))
    recipe = UniversalObject(object_id="recipe_" + key[:32], object_type="render_recipe", title=("Image-led recipe: " + brief.title)[:240],
        purpose="Bind evidence, reusable visual primitives, media provenance and creative decisions to one reproducible render.",
        parent_ids=list(versions), sources=story.sources, payload=payload.model_dump(mode="json"),
        metadata={"publication_allowed": False, "source_versions": versions, "recipe_sha256": key})
    return capture_once(store, recipe, "recipe-" + key)


def admit_recipe(store, recipe):
    payload = RenderRecipePayload.model_validate(recipe.payload)
    objects = current_objects(store)
    for key, version in payload.input_versions.items():
        if key not in objects or objects[key].version != version:
            raise ValueError("A recipe input changed; prepare a fresh recipe.")
    validate_storyboard(store, payload.storyboard_object_id)
    profile = json.loads((ROOT / "config/creative-direction.json").read_text())
    if fingerprint(profile) != payload.creative_profile_sha256 or file_hash(ROOT / "packages/media/renderer.py") != payload.renderer_sha256:
        raise ValueError("The creative profile or renderer changed after recipe preparation.")
    definitions = store.definitions()
    if fingerprint({key: value.model_dump(mode="json") for key, value in definitions.items()}) != payload.ontology_sha256:
        raise ValueError("The ontology changed after recipe preparation.")
    assert_memory_current(store, payload.governed_memory)
    if creative_settings(profile, payload.governed_memory) != payload.creative_settings:
        raise ValueError("The effective creative settings do not match the pinned recipe.")
    for asset in payload.assets.values():
        path = (ROOT / asset.asset_uri).resolve()
        allowed = {
            "image": [ROOT / ".local/assets/kinetic", ROOT / "assets/media/commons", ROOT / "assets/media/generated"],
            "font": [ROOT / "assets/fonts/barlow-condensed"],
        }.get(asset.asset_kind, [])
        if asset.asset_kind == "procedural_audio":
            if path != ROOT / "scripts/render_kinetic_video.py":
                raise ValueError("Only the pinned procedural soundtrack generator is supported.")
        elif not any(path.is_relative_to(directory) for directory in allowed):
            raise ValueError("Media must remain in the allowed asset directories.")
        if not asset.private_preview_allowed or asset.rights_state == "denied":
            raise ValueError("An asset is not available for private creative review.")
        if file_hash(path) != asset.sha256:
            raise ValueError("Media bytes changed; review their new asset version.")
    return payload
