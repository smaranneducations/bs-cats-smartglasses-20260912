#!/usr/bin/env python3
"""Load private research without network requests, credentials or approvals.

Stable IDs make reruns additive. Existing objects, including human edits,
are retained unchanged. This is not an automatic collection pipeline.
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts.business_fit import assess_fit
from packages.contracts.object import ActorType, SourceReference, UniversalObject
from packages.contracts.store import LocalObjectStore, ObjectNotFoundError

OBSERVED = datetime(2026, 9, 13, tzinfo=UTC)
ONE_URL = "https://us.shop.xreal.com/products/xreal-one-pro"
AIR_URL = "https://us.shop.xreal.com/products/xreal-air-2-pro"
PROGRAM_URL = "https://www.xreal.com/visionaries"


def reference(identifier, url, title):
    return SourceReference(source_id=identifier, uri=url, title=title, publisher="XREAL",
        captured_at=OBSERVED, notes="Manual observation dated 2026-09-13. Midnight normalizes a date, "
        "not an exact retrieval time. Manufacturer statements, not independent testing. "
        "No product photography or automated-collection permission was acquired.")


ONE_SOURCE = reference("src_xreal_one_comparison_20260913", ONE_URL, "XREAL One Pro US page and comparison")
AIR_SOURCE = reference("src_xreal_air2pro_20260913", AIR_URL, "XREAL Air 2 Pro US specifications")
PROGRAM_SOURCE = reference("src_xreal_visionaries_20260913", PROGRAM_URL, "XREAL Visionaries program information")


def observation(value, source, conditions):
    return {"value": value, "source_ids": [source.source_id],
        "evidence_kind": "manufacturer_stated", "conditions": conditions,
        "observed_at": OBSERVED.isoformat(), "confidence": None}


def product(identifier, title, source, facts):
    return UniversalObject(object_id=identifier, object_type="product", title=title,
        purpose="Support a bounded comparison for online buyers of portable displays.",
        sources=[source], tags=["research_sample", "manufacturer_stated", "display"],
        payload={
            "summary": "Source-linked display-glasses research, awaiting evidence review.",
            "brand": "XREAL", "category": "display",
            "market": "US source listing; other markets not checked",
            "variant": title + "; regional package and fitting options must be checked",
            "buyer_job": "Explore a portable personal display for a compatible video-output device.",
            "fields": {key: observation(value, source, conditions) for key, (value, conditions) in facts.items()},
            "caveats": [
                "One-brand convenience sample, not representative market coverage.",
                "Manufacturer specifications are not hands-on performance findings.",
                "No current price, stock, worldwide shipping or universal device compatibility is asserted.",
                "Fit, seller terms and required accessories need buyer-specific checks.",
            ],
        }, metadata={"sample_version": "2026-09-13.1", "publication_allowed": False})


def source_policy(identifier, title, source):
    return UniversalObject(object_id=identifier, object_type="source_policy", title=title,
        purpose="Separate research access from automated, media and commercial reuse.",
        sources=[source], payload={
            "summary": "Limited manual factual observation; broader use remains unapproved.",
            "source_uri": source.uri, "publisher": "XREAL", "access": "manual_excerpt",
            "automation": "pending", "media_reuse": "pending", "commercial_reuse": "pending",
            "rights_basis": "Public manufacturer page inspected for a small private research sample. "
                "Public accessibility is not a licence for scraping, photographs or unrestricted commercial reuse.",
            "attribution": "Link to the named XREAL page and distinguish stated specifications from tested results.",
            "refresh_days": 30, "last_observed_at": OBSERVED,
        }, metadata={"refresh_active": False, "publication_allowed": False})


def feedback(identifier, title, text, improvement, classification="operating_directive"):
    return UniversalObject(object_id=identifier, object_type="feedback", title=title,
        purpose="Preserve human direction as a scoped, traceable operating input.",
        payload={"summary": title, "input": text, "classification": classification,
                 "proposed_improvement": improvement},
        metadata={"origin": "Explicit human direction in this project conversation",
                  "recorded_by": "Agent paraphrase, not a new human approval"})


def sample_records():
    fov = "Manufacturer-stated field of view; axis and measurement method are not normalized."
    brightness = "Stated maximum; optical measurement methods are not independently reconciled."
    weight = "Manufacturer-stated mass; wearer comfort cannot be inferred from mass alone."
    refresh = "Stated maximum refresh rate; supported source and mode must be checked."
    records = [
        source_policy("policy_xreal_one_research", "One series: research and rights", ONE_SOURCE),
        source_policy("policy_xreal_air2pro_research", "Air 2 Pro: research and rights", AIR_SOURCE),
        source_policy("policy_xreal_program_research", "Partner program: access and obligations", PROGRAM_SOURCE),
        product("product_xreal_air_2_pro_us", "XREAL Air 2 Pro", AIR_SOURCE, {
            "weight_g": (75, weight), "fov_deg": (46, fov),
            "refresh_hz": (120, "Maximum stated for 2D; the page lists 90 Hz for 3D."),
            "brightness_nits": (500, brightness),
            "resolution": ("1920 x 1080", "Per eye as listed by the manufacturer."),
            "display_type": ("Sony 0.55-inch Micro-OLED", "Panel description, not a tested quality rating."),
            "tracking": ("3DoF with Beam or Beam Pro", "Accessory-dependent, not native standalone tracking."),
            "dimming": ("Three electrochromic levels", "Manufacturer-listed dimming modes."),
        }),
        product("product_xreal_one_us", "XREAL One", ONE_SOURCE, {
            "weight_g": (82, weight), "fov_deg": (50, fov),
            "refresh_hz": (120, refresh), "brightness_nits": (600, brightness),
            "display_type": ("Sony 0.68-inch Micro-OLED", "From the One series comparison on the One Pro page."),
            "tracking": ("Native 3DoF; 6DoF with XREAL Eye", "6DoF requires additional hardware."),
            "dimming": ("Three electrochromic modes", "From the manufacturer comparison table."),
        }),
        product("product_xreal_one_pro_us", "XREAL One Pro", ONE_SOURCE, {
            "weight_g": (87, weight), "fov_deg": (57, fov),
            "refresh_hz": (120, refresh), "brightness_nits": (700, brightness),
            "display_type": ("Sony 0.55-inch Micro-OLED", "Panel description, not a tested quality rating."),
            "tracking": ("Native 3DoF; 6DoF with XREAL Eye", "6DoF requires additional hardware."),
            "ipd_fit": ("M: 57-66 mm; L: 66-75 mm", "Frame size must match the buyer; not a guarantee of fit."),
            "dimming": ("Three electrochromic modes", "Manufacturer-listed dimming modes."),
        }),
        feedback("feedback_online_business_20260913", "Online business and an accessible purchase path",
            "Operate entirely online. Do not select a country or industry merely because convenient data exists. "
            "Evaluate how the buyer purchases and how this business can earn, not just online content delivery.",
            "Separate audience geography, source jurisdiction, market variant and fulfilment. "
            "Require checkout, earning access, demand and maintenance evidence before a commercial commitment.", "correction"),
        feedback("feedback_reusable_content_20260913", "Reusable stories with original, authorized visuals",
            "Use energetic 30-90 second 9:16 kinetic-text videos without mechanical narration. "
            "Support distinct product, feature, comparison, category, use-case and engagement stories.",
            "Separate reusable scene primitives, workflow-specific evidence requirements and final-artifact approval."),
        feedback("feedback_evidence_20260913", "Evidence over hype, without restricting useful storytelling",
            "Keep security, legality and credibility above convenience. Evidence over hype is an editorial "
            "promise, not a ban on personality, analysis, useful commercial relationships or engaging presentation.",
            "Label factual reporting, opinion and discovery. Do not invent firsthand tests or turn a tagline into a rigid format."),
    ]
    fit = assess_fit({
        "online_operations": {"status": "pass", "reason": "The scoped product is remotely delivered research and content, without owned inventory or shipping.",
                              "source_ids": ["feedback_online_business_20260913"]},
        "international_usefulness": {"status": "pending", "reason": "International readers are intended; this sample covers US listings only and demand abroad is unmeasured."},
        "online_checkout": {"status": "pending", "reason": "A merchant page and purchase controls were observed. No checkout, delivery eligibility or order was completed.",
                            "source_ids": [ONE_SOURCE.source_id]},
        "publisher_revenue_access": {"status": "pending", "reason": "A possible invitation route exists, but there is no accepted agreement, commission schedule or active tracking relationship.",
                                     "source_ids": [PROGRAM_SOURCE.source_id]},
        "commercial_data_rights": {"status": "pending", "reason": "Limited private factual research does not establish commercial or automated reuse permission.",
                                  "source_ids": [ONE_SOURCE.source_id, AIR_SOURCE.source_id]},
        "credible_coverage": {"status": "pending", "reason": "Three products from one brand are a UI sample, not representative domain-fit coverage."},
        "authorized_media": {"status": "pending", "reason": "The UI uses an original generic illustration. A repeatable product-specific video imagery path is not established."},
        "bounded_maintenance": {"status": "pending", "reason": "A small catalogue is proposed; refresh effort and exception workload have not been measured."},
        "budget_admission": {"status": "pending", "reason": "$80 was human-reported against a $500 ceiling. Other charges remain unreconciled; paid integrations remain disabled."},
        "demand_evidence": {"status": "pending", "reason": "No measured qualified traffic, conversions, paying customers or net receipts are recorded."},
    })
    records += [
        UniversalObject(object_id="commerce_xreal_candidate", object_type="commerce_path",
            title="XREAL online purchase and possible partner route",
            purpose="Distinguish a reachable merchant from an accessible and validated earning mechanism.",
            sources=[ONE_SOURCE, PROGRAM_SOURCE], payload={
                "summary": "Research candidate only. Online-fit gates remain pending; this is not an active affiliate business.",
                "merchant_uri": ONE_URL, "program_uri": PROGRAM_URL,
                "customer_market": "US merchant evidence; international fulfilment not checked",
                "checkout": "unknown", "publisher_access": "invitation_required",
                "purchase_friction": [
                    "Product page observed; checkout and shipping eligibility are not verified.",
                    "The buyer may need a compatible source device, correct fit and extra accessories.",
                    "Returns, taxes, warranty and regional offers need seller-specific checks.",
                ],
                "obligations": [
                    "Program application and acceptance are not completed.",
                    "Program information describes recurring content and brand-use obligations; review terms before acceptance.",
                    "Editorial independence, tracking, payment and permitted territories remain unresolved.",
                ],
                "attribution_terms": "Unknown; no tracking link issued or tested.",
                "payment_terms": "Unknown; no accepted commercial agreement.", "commission_rate": None,
                "evidence_source_ids": [ONE_SOURCE.source_id, PROGRAM_SOURCE.source_id],
                "observed_at": OBSERVED,
            }, metadata={"business_fit": fit, "publication_allowed": False}),
        UniversalObject(object_id="decision_online_fit_20260913", object_type="decision_record",
            title="Retain SmartGlasses provisionally; require the full online earning path",
            purpose="Turn the financial owner's correction into reusable decision criteria.",
            parent_ids=["feedback_online_business_20260913"], sources=[ONE_SOURCE, AIR_SOURCE, PROGRAM_SOURCE],
            payload={
                "summary": "Continue reversible local SmartGlasses work; defer vehicles and commercial commitments.",
                "feedback_ids": ["feedback_online_business_20260913"], "disposition": "proposed",
                "rationale": "Available data does not prove a suitable online business. SmartGlasses retains useful existing work, "
                    "while earning access, rights, coverage, demand and maintenance gates remain pending.",
                "target_ids": ["commerce_xreal_candidate"],
                "expected_benefit": "Avoid a domain pivot or infrastructure build justified only by source abundance.",
                "evaluation": "A source-rich vehicle candidate must not win without an evidenced remotely operated earning path. "
                    "An online glasses shop must not count as affiliate approval, demand, worldwide availability or revenue. "
                    "Unknown gates must remain pending instead of being cancelled by a score.",
            }, metadata={"assessment": fit, "runtime_policy_changed": False}),
    ]
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=ROOT / ".local/object-events.jsonl")
    args = parser.parse_args()
    store = LocalObjectStore(args.store)
    inserted = retained = 0
    for item in sample_records():
        try:
            store.get(item.object_id)
        except ObjectNotFoundError:
            store.capture(item, actor_id="research-agent", actor_type=ActorType.agent,
                          idempotency_key="seed-20260913-" + item.object_id)
            inserted += 1
        else:
            retained += 1
    print(f"Loaded {inserted} new research records; retained {retained} existing sample records without changes.")
    print("No network requests, provider credentials, paid services, human approvals or publication were used.")


if __name__ == "__main__":
    main()
