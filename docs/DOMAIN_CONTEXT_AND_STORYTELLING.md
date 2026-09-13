# Domain context and storytelling

Status: schema and policy defined; contextual warehouse population and production-agent wiring are not yet complete.

## Why this layer exists

A product table can answer specification questions, but it cannot explain why a capability matters, which audience problem it addresses, how the surrounding technology is changing or which external event changed the decision. Domain context makes those relationships explicit and reusable instead of repeatedly asking a model to reconstruct them from a large prompt.

The goal is not to collect every possible fact. The goal is to maintain the smallest governed context graph that improves decisions, stories and commercial usefulness while preserving evidence, rights, privacy, freshness and correction lineage.

## Context object model

The canonical machine contract is [`config/domain-context.schema.json`](../config/domain-context.schema.json). Every object is versioned and carries a domain, type, geographic and temporal scope, attributes, assertions, source receipts, governance state and related objects.

Supported types are:

- `domain_context`: category meaning, scope and boundaries.
- `market_snapshot`: time-scoped market estimates, pricing or adoption signals.
- `audience_segment`: validated jobs, needs, constraints and channel context.
- `industry_structure`: value chain, business models, standards and distribution.
- `technology_concept`: stable capability definitions and relationships.
- `technology_maturity_snapshot`: dated maturity, dependency and limitation assessments.
- `company_snapshot`: dated company observations, including market capitalization when relevant.
- `regulatory_event` and `industry_event`: dated external changes.
- `adoption_signal`: an observed indicator with a defined method, not an assumed trend.
- `ecosystem_relationship`: versioned links among companies, platforms, suppliers and developers.
- `trend_assertion`: an evidence-backed interpretation with confidence and expiry.
- `narrative_angle`: a reusable question and treatment, not a factual assertion by itself.

## Market cap is not market size

Company market capitalization is a volatile observation about a listed company. It needs a timestamp, currency, exchange or listing identity and source. Industry market size is an estimate about a defined market and needs a period, geography, currency, methodology and source.

The two values cannot be substituted. Neither proves product quality, customer demand, channel eligibility or our revenue potential. Forecasts remain forecasts and must never be presented as observed results.

## Audience context without profiling

Audience objects focus on jobs to be done, needs, constraints, literacy, purchase stage, channel context, price sensitivity, accessibility needs and privacy concerns. Initial segments are hypotheses until supported by evidence or direct validation.

The system must not infer protected or sensitive traits, build covert individual profiles or turn demographic assumptions into facts. Personal behavior data requires a lawful purpose, minimization, access control and applicable retention handling.

## Technology and industry context

Technology concepts describe capabilities and trade-offs across display and optics, sensing, input, compute, power, connectivity, operating systems, app ecosystems, AI, privacy, security, accessibility and interoperability. A maturity snapshot adds time-dependent readiness, dependencies and limitations.

Industry objects capture category boundaries, value chain, business models, standards, regulation, distribution, adoption drivers and barriers. This allows a story to explain an ecosystem or a change even when no individual product is the main subject.

## Contextual story contract

The selection and safety rules are defined in [`config/contextual-storytelling-policy.json`](../config/contextual-storytelling-policy.json). Every candidate story declares:

- a target audience and useful decision question;
- the exact context objects and assertions it uses;
- one visual primitive and the suitable channel treatment;
- caveats, freshness boundary and evidence gaps;
- outputs that depend on it so corrections can propagate.

An infographic normally uses one to three assertions. A short video can use up to six when clarity permits and remains capped at 90 seconds. A story can focus on product impact, an audience job, a technology trade-off, an industry explainer, an ecosystem map, a regulatory change, a timeline, a qualified trend, a comparison or an important unknown.

Variation comes from selecting a useful question and recombining governed context. The system does not force novelty, invent a trend or use a commercial relationship to override factual ranking.

## Missingness, freshness and review

The existing missingness states remain meaningful: `unknown`, `not_found_yet`, `not_disclosed`, `not_applicable`, `conflicting` and `stale` are different conditions. An unrelated missing field does not prevent a useful output. A fact needed by the selected story must be sourced, qualified, omitted or escalated as a real exception.

Volatile assertions expire. A correction or replacement identifies dependent analyses and media for revalidation. Normal low-risk sourced updates can proceed under human-on-the-loop controls; conflicting, high-impact, privacy-sensitive, rights-unclear or publication-critical cases use exception review. The exact final artifact and metadata still require the publication gate.

## SmartGlasses seed ontology

[`config/domains/smart-glasses-context.json`](../config/domains/smart-glasses-context.json) defines the initial taxonomy and audience hypotheses. It intentionally contains no invented market numbers. It distinguishes display-first, audio-first, camera-first, AI-companion and spatial-computing capabilities because a product label alone does not establish comparability.

This seed enables future stories about technology impact, audience jobs, ecosystem dependencies, privacy and regulation, timelines and evidence gaps. Each factual population step still needs a source receipt and applicable rights.

## Implementation sequence

1. Validate the context schema and map its IDs into the existing context envelope.
2. Create warehouse tables from the schema after the durable cloud application layer is available.
3. Populate stable definitions first, then evidence-backed snapshots and events with deduplication and expiry.
4. Add context retrieval to analysis and content agents using the smallest relevant context set.
5. Generate story candidates, score usefulness and evidence quality, and route only real exceptions to the operator.
6. Link approved outputs to their context dependencies for correction and freshness revalidation.

Until those steps are implemented and tested, the files in this change are architecture contracts rather than proof of a populated or production-connected intelligence layer.
