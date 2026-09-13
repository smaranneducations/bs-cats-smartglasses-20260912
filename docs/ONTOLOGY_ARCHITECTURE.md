# Ontology and semantic architecture

Status: version 1 design authority. Date: 2026-09-13.

## Decision

The platform will keep its current lightweight, versioned JSON object model while aligning identifiers and semantics with established web standards. It will not add a graph database merely to appear sophisticated. The first objective is consistent meaning, validation, lineage, impact analysis, and portability through interfaces that can later serialize to JSON-LD or RDF.

## Standards profile

| Standard | Adopted pattern | Version 1 implementation |
| --- | --- | --- |
| SKOS | Stable concept identifiers, labels, broader, narrower, related and cross-scheme mappings | Concept registry and ontology tree; mappings are an additive extension |
| SHACL | Separate immutable data and shapes inputs, constraints and machine-readable reports | Contract and domain validation; SHACL export is planned |
| PROV-O | Entity, activity and agent lineage with derivation and attribution | Object versions, actors, input versions, sources and receipts |
| DCAT 3 | Dataset catalog, distributions, services, versions, quality and qualified relations | Domain and dataset registry; formal DCAT export is planned |
| ODRL | Permission, prohibition, duty and constraints for assets | Source and media policy classification; ODRL export is planned |
| JSON-LD 1.1 | Linked identifiers in developer-friendly JSON | Context and identifier profile is planned |

Primary references: [SKOS](https://www.w3.org/TR/skos-reference/), [SHACL](https://www.w3.org/TR/shacl/), [PROV-O](https://www.w3.org/TR/prov-o/), [DCAT 3](https://www.w3.org/TR/vocab-dcat-3/), [ODRL 2.2](https://www.w3.org/TR/odrl-model/), and [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/).

## Evaluated libraries

[RDFLib](https://github.com/RDFLib/rdflib) is the leading Python candidate for RDF and JSON-LD serialization. [pySHACL](https://github.com/RDFLib/pySHACL) is the leading Python candidate for standards-based SHACL validation and uses RDFLib. [OWLAPI](https://github.com/owlcs/owlapi) is mature but introduces a Java runtime and is unnecessary for the current bounded Python system.

No library is added in this release. RDFLib and pySHACL should enter through a measured proof of concept after stable concept mappings and validation-report contracts exist. This avoids a dependency and reasoning engine before a concrete query, validation and performance need is proven.

## Semantic object model

| Object | Meaning |
| --- | --- |
| Concept scheme | Domain-bounded collection of stable concepts |
| Concept | Stable identity for a meaning, independent of one label or source column |
| Definition | Versioned description, datatype, unit, applicability, cardinality, examples and confidence policy |
| Relation | Typed broader, narrower, related, part, prerequisite, compatible, substitute or causal-hypothesis link |
| Shape | Deterministic constraints applied to one object type or workflow boundary |
| Entity | Real or conceptual thing being described, with explicit market and variant identity |
| Assertion | Subject, predicate, value, unit, scope, time, source, evidence, method and confidence reason |
| Observation | Attributed human or machine observation that is not automatically a verified assertion |
| Evidence | Retrievable support with source identity, observation time, rights and retention policy |
| Derivation | Exact input versions, activity, actor, rule or model profile and output version |
| Policy | Permission, prohibition, duty, constraint and decision authority for an asset or action |
| Validation result | Immutable report of shape, focus object, path, severity, evidence and remediation |

## Design rules

Concept identifiers never encode a mutable label, vendor taxonomy, or database column position. Definitions can change without changing concept identity when meaning remains compatible. A meaning change creates a new concept or an explicit migration relationship.

Unknown, not applicable, not observed, conflicting, withdrawn, false and supported are distinct states. Confidence is not a decorative percentage; it identifies method and reasons. Manufacturer statements, independent measurements, human observations, inferred analyses and audience opinions remain separate evidence classes.

Products are compared only at an explicit variant, market, time, unit and measurement regime. Source identifiers are not product identities. A correction identifies affected assertions, analyses, scripts, renders, releases and metrics so dependent artifacts can be revalidated.

Hierarchy and association are different. Direct broader or narrower links are stored separately from inferred transitive ancestry. External mappings use exact, close, broad, narrow or related semantics and retain mapping provenance.

Shapes validate data without mutating it. Validation reports are first-class objects and may drive exceptions, but do not silently repair production knowledge. Recursive or computationally unbounded rules are rejected from synchronous workflows.

Rights attach to the exact asset and action. “Available online” is not permission. A policy records target, assigner, assignee where known, allowed actions, prohibited actions, duties such as attribution, territory and time constraints, and evidence of observed terms.

## Ontology evolution

1. Capture feedback as an observation or proposal linked to affected concepts and workflows.
2. Classify the change as additive, compatible definition revision, breaking semantic change, mapping change, constraint change, or policy change.
3. Produce impact analysis over data, forms, agents, analyses, content and released artifacts.
4. Add evaluation cases that distinguish expected old and new behavior.
5. Require administrator review for breaking meaning, rights, permissions, ranking policy, or public claims.
6. Version the concept scheme and migration plan.
7. Revalidate affected objects and retire superseded definitions without erasing history.
8. Promote only after acceptance evidence; roll back by restoring the prior active definition and invalidating incompatible derivatives.

## Strategic advantage

There is no hidden ontology trick that guarantees commercial advantage. The defensible opportunity is the compounding combination of stable meaning, source and rights lineage, versioned corrections, decision-quality evaluations, reusable creative primitives, and measured downstream performance. That combination lets the same knowledge safely power comparisons, reports, media, APIs, and future domains while reducing repeated research and review.
