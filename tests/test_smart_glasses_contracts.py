import unittest

from pydantic import ValidationError

from packages.contracts import SourceReference
from packages.contracts.smart_glasses import (
    ClaimKind,
    CommercialIntent,
    EvidenceClaim,
    EvidenceTier,
    SmartGlassesObject,
    SmartGlassesObjectType,
    SmartGlassesPayload,
    VerificationState,
)


class SmartGlassesContractTests(unittest.TestCase):
    def test_valid_claim_is_linked_to_structured_source(self):
        source = SourceReference(
            source_id="src_manufacturer",
            uri="https://example.test/product",
            publisher="Example manufacturer",
        )
        item = SmartGlassesObject(
            object_id="obj_product_signal",
            object_type=SmartGlassesObjectType.product,
            title="Example product profile",
            purpose="Test evidence-linked domain data.",
            sources=[source],
            payload=SmartGlassesPayload(
                summary="A source-linked profile.",
                claims=[
                    EvidenceClaim(
                        claim_id="claim_weight",
                        statement="The manufacturer publishes a product weight.",
                        kind=ClaimKind.fact,
                        source_ids=[source.source_id],
                        evidence_tier=EvidenceTier.primary_manufacturer,
                        verification_state=VerificationState.verified,
                        confidence=0.95,
                    )
                ],
            ),
        )
        self.assertEqual(item.domain, "smart_glasses")

    def test_weak_evidence_cannot_be_marked_verified(self):
        with self.assertRaises(ValidationError):
            EvidenceClaim(
                claim_id="claim_rumor",
                statement="A community rumor is treated as fact.",
                kind=ClaimKind.fact,
                source_ids=["src_forum"],
                evidence_tier=EvidenceTier.community_report,
                verification_state=VerificationState.verified,
                confidence=0.8,
            )

    def test_commercial_intent_requires_disclosure(self):
        with self.assertRaises(ValidationError):
            SmartGlassesPayload(
                summary="A commercial comparison.",
                commercial_intent=CommercialIntent.affiliate,
                disclosure_required=False,
            )


if __name__ == "__main__":
    unittest.main()
