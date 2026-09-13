from __future__ import annotations

from hashlib import sha256
from math import ceil
from packages.contracts.audience import CardBundlePayload, ContentCardPayload, ShortsPlanPayload
from packages.contracts.object import UniversalObject
from packages.contracts.store import ContractViolationError
from packages.contracts.workflows import project_field_claim


THEMES = [
    ("visual_workspace", "A bigger-looking workspace", ["display_type", "resolution", "fov_deg", "brightness_nits"],
     "Read display scale, clarity and brightness together; no single number proves comfort or quality."),
    ("motion_and_stability", "Motion that fits the task", ["refresh_hz", "tracking", "dimming", "fov_deg"],
     "Refresh, tracking and lens control shape different parts of a moving-screen experience."),
    ("fit_and_wearability", "What wearing it may require", ["weight_g", "ipd_fit", "prescription", "included_accessories"],
     "Physical fit and required extras can matter more than a headline specification."),
    ("device_compatibility", "Check the complete connection", ["connection", "phone_support", "pc_support", "included_accessories"],
     "A display is useful only when the source device, port, software and accessories work together."),
    ("ownership", "Look beyond the box", ["warranty", "included_accessories", "charging_case", "prescription"],
     "Ownership includes regional warranty, fitting and accessories, not only the initial device."),
    ("mobile_use", "What changes away from a desk", ["weight_g", "battery_hours", "offline_features", "water_resistance"],
     "Portability depends on power, offline behavior, durability and what must travel with the product."),
    ("communication", "How the product handles sound and capture", ["audio", "microphones", "camera_mp", "video_modes"],
     "Audio and capture specifications describe capabilities, not recording quality or social acceptability."),
    ("privacy", "Visible signals and privacy limits", ["privacy_indicator", "camera_mp", "video_modes", "ai_features"],
     "Recording indicators and camera features should be considered together with local rules and human expectations."),
]


def _identity(parts):
    return sha256(":".join(str(part) for part in parts).encode()).hexdigest()[:32]


def _candidate_groups(product, limit):
    fields = product.payload.get("fields", {})
    known = {key for key, value in fields.items() if value.get("value") is not None and value.get("source_ids")}
    result, seen = [], set()
    for theme, hook, preferred, impact in THEMES:
        key = next((item for item in preferred if item in known and item not in seen), None)
        if key is None:
            continue
        seen.add(key)
        result.append((theme, hook, [key], impact))
        if len(result) >= limit:
            return result
    if len(result) < limit:
        for key in sorted(known - seen):
            result.append(("evidence_snapshot", "One documented detail worth checking", [key],
                "Read this source-linked detail with its market, variant and evidence conditions visible."))
            if len(result) >= limit:
                return result
    return result


def compose_audience_package(store, product, max_cards=6, duration_seconds=60):
    if product.object_type != "product" or product.status.value != "active" or product.review.state.value != "approved":
        raise ContractViolationError("Audience cards require an active, human-approved product version.")
    if not 3 <= max_cards <= 12:
        raise ContractViolationError("Compose between three and twelve bounded cards.")
    if not 30 <= duration_seconds <= 90:
        raise ContractViolationError("A Short must last between 30 and 90 seconds.")
    definitions = store.definitions()
    candidates = _candidate_groups(product, max_cards)
    if len(candidates) < 3:
        raise ContractViolationError("At least three distinct evidence-compatible cards are required.")
    cards = []
    for theme, hook, keys, impact in candidates[:max_cards]:
        claims, source_ids = [], set()
        for key in keys:
            claim, _ = project_field_claim(product, key, definitions)
            claims.append(claim)
            source_ids.update(claim["source_ids"])
        card_id = "card_" + _identity([product.object_id, product.version, theme, *keys, "semantic-card-composer-2"])
        payload = ContentCardPayload(summary=f"{theme.replace('_', ' ').title()} card for {product.title}.",
            product_id=product.object_id, product_version=product.version, theme=theme,
            hook=hook, practical_impact=impact, field_keys=keys, claims=claims,
            source_ids=sorted(source_ids))
        cards.append(UniversalObject(object_id=card_id, object_type="content_card",
            title=f"{product.title}: {hook}", purpose="Present one source-linked attribute as one useful audience insight.",
            parent_ids=[product.object_id], sources=[source for source in product.sources if source.source_id in source_ids],
            payload=payload.model_dump(mode="json"), metadata={"composer_revision": 2,
                "input_versions": {product.object_id: product.version}, "publication_allowed": False}))
    bundle_id = "bundle_" + _identity([product.object_id, product.version, *[card.object_id for card in cards]])
    bundle_payload = CardBundlePayload(summary=f"Governed audience-card bundle for {product.title}.",
        product_versions={product.object_id: product.version},
        card_versions={card.object_id: card.version for card in cards},
        themes=[card.payload["theme"] for card in cards])
    bundle = UniversalObject(object_id=bundle_id, object_type="card_bundle", title=f"Audience cards: {product.title}",
        purpose="Group reusable approved-product insight cards for channel-specific presentation.",
        parent_ids=[product.object_id, *[card.object_id for card in cards]],
        payload=bundle_payload.model_dump(mode="json"), metadata={"publication_allowed": False})
    selected = cards[:1]
    count = max(3, ceil(duration_seconds / 15))
    base = duration_seconds / count
    durations = [round(base, 3) for _ in range(count)]
    durations[-1] = round(duration_seconds - sum(durations[:-1]), 3)
    card = selected[0]
    scenes = [{"scene_id": f"scene_{index + 1:02d}", "card_id": card.object_id,
               "card_version": card.version, "duration_seconds": durations[index]}
              for index in range(count)]
    plan_payload = ShortsPlanPayload(summary=f"Private 9:16 Shorts plan from the {product.title} card bundle.",
        card_bundle_id=bundle.object_id, card_bundle_version=bundle.version,
        card_versions={card.object_id: card.version for card in selected},
        duration_seconds=duration_seconds, scenes=scenes)
    plan_id = "shorts_" + _identity([bundle.object_id, bundle.version, duration_seconds, "atomic-kinetic-card-2"])
    plan = UniversalObject(object_id=plan_id, object_type="shorts_plan", title=f"YouTube Short plan: {product.title}",
        purpose="Turn one governed attribute card into a private 30-90 second vertical-video plan.",
        parent_ids=[bundle.object_id, *[card.object_id for card in selected]],
        payload=plan_payload.model_dump(mode="json"), metadata={"publication_allowed": False,
            "requires_exact_artifact_approval": True})
    return cards, bundle, plan
