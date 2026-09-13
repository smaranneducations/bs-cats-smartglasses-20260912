# Incremental catalogue and missing-data policy

Version 1.0.0. Canonical interpretation of GitHub issue 15.

## Purpose

Build market breadth without fabricating completeness. A partially known product can be useful, and waiting for every ontology field would hide products, slow learning and concentrate effort on low-value gaps.

Bulk growth begins only after durable production Firestore persistence is working. Until then, the existing small local dataset is test evidence rather than a production catalogue.

## SmartGlasses discovery target

The working discovery target is 60 to 70 models. This is a planning range supplied by the human strategic partner, not a verified market count. The discovery process must resolve duplicates, regional variants, renamed products, accessories and discontinued models before reporting coverage.

Count distinct comparable product variants, not search results or type approvals. Preserve market and variant boundaries rather than merging records on model name alone.

## Minimal admission

A product may enter before all attributes are known when it has stable identity, brand and model, explicit variant/market scope or explicit unknowns, at least one lawful source receipt and an observation timestamp.

This admits a discoverable object, not a verified product profile. Each field assertion carries its own evidence, availability, confidence, freshness and policy state.

## Missingness semantics

Use structured states rather than a display string:

- `unknown`: no determination yet;
- `not_found_yet`: bounded research did not find a usable value;
- `not_disclosed`: an applicable current source omits the value;
- `not_applicable`: the concept does not apply to the scoped variant;
- `conflicting`: current assertions materially disagree;
- `stale`: prior evidence exceeded freshness policy;
- `available`: a value exists, with assurance evaluated separately.

The interface may display friendly text such as "Not available yet," but the stored state remains precise. Missingness never becomes false, zero or an inferred product fact.

## Incremental refresh

Refresh tasks are field-level and deduplicated by product, concept, source and source version or observation date. Priority goes to gaps needed by current user questions, commercial decisions, stale claims, resolvable conflicts and newly changed sources.

Do not repeat a search merely because a field is empty. Stop when the same absence is already recorded for the source version, the field has no prioritized dependency, the bounded source budget is exhausted, or rights, privacy, access or cost admission denies the attempt.

## Human observations

Human-provided data is welcome and can resolve valuable gaps. It enters as an attributed observation, not as silently verified truth. The field's evidence policy determines whether corroboration or consequential review is required.

## Output dependency

Each KPI, analysis, card, comparison and story declares required concepts. Eligibility evaluates only those dependencies plus identity, scope, evidence, confidence, freshness, rights and correction state.

An unrelated missing field does not block an output. A missing required field blocks the dependent claim or artifact, not the entire product record. Content agents may choose another supported angle instead of inventing the missing fact.

## Measurement

Track breadth and depth separately. Useful measures include distinct comparable variants, coverage of priority concepts, freshness, source diversity, accepted assertions, conflict and correction rates, useful outputs enabled, cost per accepted field and human minutes per accepted field.

A larger catalogue with weak identity or invented attributes is worse than a smaller governed catalogue. The goal is increasing useful coverage at sustainable cost.
