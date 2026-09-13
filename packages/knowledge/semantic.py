"""Domain tools over versioned records. No arbitrary SQL or model calls."""

from datetime import datetime
from hashlib import sha256
import json
from types import SimpleNamespace

from .projection import project_record, scalar, stamp, RETIRED


class SemanticTools:
    def __init__(self, store):
        self.store = store

    def ontology(self, keys=None):
        definitions = self.store.definitions()
        requested = list(keys) if keys else list(definitions)
        missing = sorted(set(requested) - set(definitions))
        if missing:
            raise ValueError("Unknown concepts: " + ", ".join(missing))
        items = []
        concepts = []
        definition_rows = []
        for key in requested:
            definition = definitions[key].model_dump(mode="json")
            definition_hash = sha256(
                json.dumps(definition, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            concept_id = "concept_" + key
            items.append({"concept_id": concept_id, "definition_hash": definition_hash, **definition})
            concepts.append({
                "concept_id": concept_id,
                "definition_hash": definition_hash,
                "canonical_name": key,
                "label": definition["label"],
                "category": definition["category"],
                "value_type": definition["value_type"],
                "canonical_unit": definition.get("unit"),
                "status": "active",
            })
            definition_rows.append({
                "concept_id": concept_id,
                "definition_hash": definition_hash,
                "definition": definition["description"],
                "constraints": {
                    "minimum": definition.get("minimum"),
                    "maximum": definition.get("maximum"),
                    "category": definition["category"],
                    "value_type": definition["value_type"],
                    "unit": definition.get("unit"),
                },
                "origin": "current_registry",
            })
        return {
            "definition_basis": "current_registry",
            "concepts": concepts,
            "definitions": definition_rows,
            "relationships": [],
            "rules": [],
            "items": items,
        }

    def _record(self, object_id, as_of=None):
        history = self.store.history(object_id)
        if as_of is not None:
            limit = datetime.fromisoformat(stamp(as_of))
            history = [record for record in history
                       if datetime.fromisoformat(stamp(record.event.occurred_at)) <= limit]
        if not history:
            raise ValueError("No recorded version exists at that time.")
        return max(history, key=lambda record: record.snapshot.version)

    def assertions(self, product_id, concepts=None, as_of=None):
        from packages.governance.review_routing import classify_review
        record = self._record(product_id, as_of)
        item = record.snapshot
        review_route = classify_review(item)
        if item.object_type != "product":
            raise ValueError("Choose a product object.")
        definitions = self.store.definitions()
        keys = list(concepts) if concepts else list(item.payload.get("fields", {}))
        self.ontology(keys)
        rows = project_record(record, definitions)
        selected = {"concept_" + key for key in keys}
        return {
            "product_id": item.object_id, "title": item.title, "version": item.version,
            "category": item.payload["category"], "market": item.payload["market"],
            "variant": item.payload.get("variant"), "status": scalar(item.status),
            "review_state": review_route.display_state,
            "human_action_required": review_route.required,
            "as_of": stamp(as_of), "time_basis": "recorded knowledge, not inferred real-world validity",
            "definition_basis": "current_registry; historical ontology reconstruction not yet available",
            "assertions": [row for row in rows["catalog_assertions"] if row["concept_id"] in selected],
            "sources": rows["evidence_sources"], "evidence": rows["evidence_items"],
            "missing_concepts": sorted(selected - {row["concept_id"] for row in rows["catalog_assertions"]}),
            "publication_eligible": False,
        }

    def compare(self, product_ids, concepts, as_of=None):
        if not 2 <= len(product_ids) <= 4 or len(set(product_ids)) != len(product_ids):
            raise ValueError("Compare two to four distinct products.")
        if not concepts or len(concepts) > 25 or len(set(concepts)) != len(concepts):
            raise ValueError("Choose one to 25 distinct concepts.")
        products = [self.assertions(oid, concepts, as_of) for oid in product_ids]
        if len({product["category"] for product in products}) != 1:
            raise ValueError("Cross-category specification ranking is not supported.")
        if any(product["status"] in RETIRED for product in products):
            raise ValueError("Retired records cannot supply a current comparison.")
        rows = []
        for definition in self.ontology(concepts)["items"]:
            cells = []
            for product in products:
                assertion = next((item for item in product["assertions"]
                                  if item["concept_id"] == definition["concept_id"]), None)
                cells.append({"product_id": product["product_id"], "assertion": assertion,
                              "missing": assertion is None})
            rows.append({"concept": definition, "cells": cells, "winner": None})
        return {"products": products, "rows": rows, "automatic_winner": False,
                "caveat": "Markets, variants, conditions and reference-only evidence remain explicit."}
