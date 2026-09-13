# SmartGlasses UAT report

Date: 2026-09-13
Tester: Bhasker
Environment: local workspace at `http://127.0.0.1:8766/`

This report records user-observed behavior. A passed interaction does not establish source accuracy, media rights, cloud deployment, publication readiness or revenue.

## UAT-001: Inspect product evidence

Status: Passed

- The tester opened the Intelligence desk and inspected VITURE Luma Pro, Regular.
- The interface displayed the product's recorded attributes and clearly showed the review state as pending.
- Pending is the correct state before human factual review.

## UAT-002: Compare two products

Status: Partially passed; correction required

- The tester selected VITURE Luma Pro, Regular and RayNeo Air 4 Pro, Standard, selected comparison concepts and opened the comparison inspection view.
- Comparison navigation and inspection worked.
- The concept selector exposes only a small hard-coded subset even though the display-glasses ontology currently defines 19 applicable attributes.
- The selector includes battery life, which is not applicable to these wired display-glasses records.

Expected correction:

- Generate available comparison concepts from the ontology and the selected product category.
- Present all applicable concepts, grouped for usability.
- Show coverage such as `2/2`, `1/2` or `0/2` for the selected products.
- Preserve missing values as Unknown.
- Mark or prevent misleading direct comparison where measurement regimes are not normalized.
- Do not remove access to lower-coverage concepts merely to simplify the interface.

Acceptance criteria:

- For two display products, the selector is derived from the 19 applicable display/common concepts rather than a fixed list.
- Camera/audio-only concepts do not appear unless applicable to at least one selected product and are clearly labeled when categories differ.
- Selecting any offered concept produces a source-linked result or an explicit Unknown value for each product.
- Existing evidence, review and publication safeguards remain unchanged.

## UAT-003: Human review of product data

Status: In progress

- The review interface provides version-specific notes and the actions Approve record, Needs changes and Reject.
- Approval applies only to the displayed record version. It does not publish content, clear media rights or authorize spending.
- The tester will next review and decide the two product records used in UAT-002.

## Deferred end-to-end boundaries

- BigQuery tables exist but product facts are not yet loaded and used by the application.
- Firestore exists but local workflow persistence remains active.
- The cloud API is not deployed.
- Source-policy and media-rights review remain separate from product factual approval.
- Exact final-video and metadata approval remains mandatory before publication.

## UAT-004: Review inbox decision taxonomy

Status: Correction required

- The tester approved VITURE Luma Pro, Regular. The persisted product is now v2 with review state `approved`; the interface presents the decision status as active.
- The approval interaction works, but the Review inbox places unrelated review responsibilities in one flat list of records.
- A human reviewer cannot efficiently distinguish a product-data decision from governance, agent, ontology, media-rights, release or commercial decisions.

Expected correction:

- Classify every review item by decision responsibility, independently of its low-level object type.
- Provide categories for Governance and charter, Agents and workflows, Ontology and schema, Data and evidence, Content and editorial, Media and rights, Release and publication, and Commerce.
- Show category counts and filters, then show risk, required human role, exact object version, blocked dependencies and the consequence of approval on each card.
- Keep factual approval, source permission, media rights, spending authority and exact-artifact publication approval as separate decisions even when they affect the same output.
- Allow a unified `All` view, but do not make the unstructured list the primary review experience.

Acceptance criteria:

- Each pending item has one primary review category and may declare related secondary categories.
- Reviewers can filter the inbox without losing pending items or changing their state.
- Product data appears under Data and evidence; source-policy records appear under Media and rights or Data-source rights as applicable.
- Agent profiles and executions do not appear as product-data reviews.
- Approval copy states exactly which authority is granted and which authorities remain unchanged.
- The category is metadata-driven so future object types do not require a one-off page rewrite.

Traceability:

- Governed feedback object: `feedback_review_inbox_taxonomy_20260913` v1, pending disposition review.

## UAT-005: Feedback and decision workspace taxonomy

Status: Correction required

- The Feedback and decisions page separates captured feedback from proposed decisions, but does not organize either list by the affected system area.
- A classification such as correction, preference or ontology gap describes the nature of feedback; it does not answer whether the item affects governance, ontology, data capture, agents, content, rights, release or commerce.
- Lifecycle state and subject area must remain separate dimensions. For example, an ontology-gap feedback item can lead to a proposed ontology decision and later an active or retired ontology rule.

Expected correction:

- Add a subject-area taxonomy shared by feedback, decisions and review queues.
- Initial categories: Governance and charter, Agents and workflows, Ontology and schema, Data capture and evidence, Content and editorial, Media and rights, Release and publication, Commerce, and Cost and operations.
- Show category counts, filters and category labels on every feedback and decision card.
- Show lifecycle separately: captured feedback, proposed decision, active, deferred, rejected, superseded or retired.
- Show affected object IDs, workflow families, evaluation cases and downstream impact where applicable.
- Provide a focused view for one category without hiding cross-category dependencies.

Acceptance criteria:

- The user can answer both "what kind of feedback is this?" and "which system area does it affect?" from every card.
- Filtering by Ontology and schema shows ontology-gap feedback, its resulting proposed decisions and active ontology changes without mixing unrelated media or commercial items.
- Category assignment is stored as governed metadata and is not inferred only from display text.
- Existing feedback history, review state and permission boundaries remain unchanged.

Traceability:

- Governed feedback object: `feedback_learning_workspace_taxonomy_20260913` v1.
- Related finding: UAT-004 / `feedback_review_inbox_taxonomy_20260913` v1.
