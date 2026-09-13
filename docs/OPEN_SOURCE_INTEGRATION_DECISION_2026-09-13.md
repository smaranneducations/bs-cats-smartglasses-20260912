# Open-source capability integration decision

Decision date: 2026-09-13

## Outcome

Use external projects as bounded capabilities behind the existing object, policy,
cost and audit contracts. Do not replace the platform with three additional
applications or treat repository popularity as evidence of business value.

## Archify: adopt now

Archify converts typed JSON into deterministic architecture, workflow, sequence,
data-flow and lifecycle HTML/SVG artifacts. Its MIT license permits use and
modification with preservation of the license notice. This directly improves the
operator's documentation layer without requiring a hosted service or provider
credential.

- Installed as a user-level Codex skill, not a project dependency.
- Typed diagram sources live in `docs/architecture/`.
- `scripts/generate_architecture_docs.sh` disables Archify's optional network
  update check and regenerates the HTML artifact locally.
- The operator exposes the map under Learn and improve / Capability integrations.

Source: https://github.com/tt-a1i/archify

## OpenSEO: adopt the workflow boundary, not the application stack

OpenSEO covers keyword research, rank tracking, competitor insights, backlinks,
site audits and AI visibility. Its repository is MIT-licensed, but useful SEO data
depends on a DataForSEO credential and per-request charges. Copying its React,
authentication, database and Cloudflare stack would duplicate our control plane.

A future bounded adapter will normalize licensed results into market observations,
feedback signals and decision records. Popularity remains separate from factual
product evidence. The adapter stays disabled until a public property, measurable
buyer question and costed experiment exist.

Source: https://github.com/every-app/open-seo

## MiniMind: preserve an adapter contract, defer execution

MiniMind is an Apache-2.0 educational implementation of a small language model and
training pipeline. It offers OpenAI-compatible serving options, but its model
downloads, hardware needs and task quality are not evaluated for this platform.
Installing weights now would add complexity without proving lower cost per accepted
result.

A future evaluation may route one low-risk classification or extraction task to a
local endpoint and compare acceptance quality, repairs, latency and total cost. No
private object history will be used for training by default.

Source: https://github.com/jingyaogong/minimind

## Cost and security disposition

This integration creates no paid provider request, subscription, cloud resource,
model download or training job. Archify receives only a bounded local diagram
specification. OpenSEO and MiniMind remain disabled until their separate data,
quality and cost gates pass.
