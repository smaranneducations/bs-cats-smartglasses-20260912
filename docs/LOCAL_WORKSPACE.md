# Private local workspace

Implementation checkpoint: 2026-09-13. This is a local research and review
application, not a deployed or revenue-generating autonomous business.

## Open and run

The new workspace uses http://127.0.0.1:8766/. The earlier video demo on port
8765 is separate and is not replaced.

Use the project's existing Python environment; no new installation is required:
```sh
.venv/bin/python scripts/seed_workspace.py
.venv/bin/python scripts/serve_workspace.py --port 8766
```

The seed script captures three XREAL display-glasses records, three source
policies, three feedback records, one commerce candidate and one proposed
decision. Reruns do not overwrite existing sample objects. All newly captured
records remain unapproved. The small one-brand sample does not meet the
representative domain-fit coverage milestone.

## Implemented components

- Private local operator session on loopback; separately configured scoped
  reader, editor, agent and reviewer API credentials.
- SQLite snapshots, transactional history, request deduplication and
  revision-aware API edits/reviews. Existing JSONL history is preserved and
  imported; imported identities remain explicitly unverified.
- Catalogue, comparison, evidence detail, review inbox, field definitions,
  feedback, proposed decisions, source-policy and commerce screens.
- Twenty-five built-in semantic fields. Missing values are distinct from
  false/zero; conditions are kept beside specifications.
- Draft composers for ten story families, plus two gated families.
  These are brief-generation scaffolds, not twelve complete agent workflows
  or a connected automated rendering pipeline.
- A deterministic online-fit assessment that preserves failed and unknown
  gates instead of inventing a commercial score. The seed assessment is
  advisory, not permission for paid work, policy changes or publication.

## Evidence and limitations

The sample paraphrases limited manufacturer specifications from:

- [One Pro US page and One series comparison](https://us.shop.xreal.com/products/xreal-one-pro)
- [Air 2 Pro US specifications](https://us.shop.xreal.com/products/xreal-air-2-pro)
- [Visionaries program information](https://www.xreal.com/visionaries)

Observation date: 2026-09-13. Date-only observations use midnight UTC as a
normalization convention, not a precise retrieval time. Manufacturer
statements are not independent tests. No worldwide availability, completed
checkout, active affiliate agreement, current prices, stock or revenue is claimed.

Automation, commercial reuse and product-image reuse remain pending. The
generic glasses illustration is original code artwork, not a photograph or
a representation of a specific model. No remote product images are copied.

## Evidence-handling corrections and checks

Authorized correction pass: 2026-09-13.

- Product edits preserve observation times, multiple source references and
  confidence unless explicitly changed. New sources can be attached to
  existing products. Existing source identifiers cannot be silently retargeted.
- Drafts retain units, conditions and evidence types. Unassessed confidence
  stays null; zero stays zero. Independent reports remain unassessed rather
  than automatically becoming reputable or verified evidence.
- Workflow drafts carry typed product-version lineage. Changed inputs block
  backend approval as well as the interface; ordinary edits cannot relabel
  lineage. Recompose older workflow drafts that lack this lineage.
- Actual request bytes are bounded, including chunked requests without a
  Content-Length header. Nonfinite numeric evidence is rejected.
- API fixtures use scoped credentials and explicit revisions. Storage checks
  target SQLite. The container recipe now includes web assets, but no
  container build or deployment has been performed.

Observed checks:

- 30 Python tests passed across API, object workflow, SmartGlasses contracts,
  research intake, content review packets and governance regressions.
- 8 JavaScript evidence-form regression tests passed.
- Isolated browser edits retained all eight original observation dates,
  saved an added source alongside the original, preserved zero confidence
  and left other confidence values unassessed.
- Browser comparison and sourced comparison-brief creation completed.
  After an input edit, the loaded draft displayed its warning and disabled
  approval. The independent API regression also rejected stale approval.
- The overview was visually inspected at 1280 x 900 and 375 x 812. Document
  width matched each viewport without horizontal page overflow. No captured
  browser console errors were reported during the exercise.
- Browser mutations used disposable data, not the real catalogue. Test
  activity is not human factual approval or a publishing decision.

These are focused checks, not an exhaustive browser matrix, full security
audit, production deployment test or verification of product specifications.
An additive production-planning slice was subsequently validated with the
human's explicit approval: all 62 tests passed, including 13 new tests.

Priority correction, 2026-09-13: consult
docs/FOUNDATION_REALITY_CHECK_2026-09-13.md before continuing presentation
expansion. The BigQuery path, agent runtime and semantic/feedback execution
layer are not established by the local demos. The preferred creative
direction is image-led, colourful and music-backed, without mechanical
narration; config/creative-direction.json is specified but not yet enforced.
The comparison preview reached its final 90-second scene; source blockers,
proposal-form opening and routine-job inbox exclusion were exercised.
Three private 90-second H.264 MP4 drafts were exported with source-review
packets and lineage manifests. No paid API calls or publishing occurred.
Intermediate-window-width overflow remains unresolved; do not call browser
QA complete. See docs/PRODUCTION_PLANNING.md and the private checkpoint
.local/governance/VALIDATION_EXPORT_HANDOFF_2026-09-13.md for artifacts,
actual checks, remaining gates and the next useful slice.

## Security, cost and next milestone

The launcher does not load .env and needs no provider keys. A loopback
operator session trusts the person using this computer; it is not a remote
multi-user identity system. Do not expose or tunnel it to the internet.

The database is private local project data, not a secret store. Git/container
exclusions and file permissions do not prove that the parent OneDrive folder
is excluded from synchronization. Previously disclosed credentials need
separate rotation/storage decisions; none were used or printed here.

The overview labels $80 as human-reported subscription spend and other costs
as unreconciled. It is not a live bill or a completed financial ledger.
No paid API call, cloud deployment or public upload is part of this slice.

Next: implement source-policy editing and rights-admitted bounded refresh,
then connect workflow-specific rendering, broader dependency invalidation
and measured cost/demand tracking. Broader H1 and the full commercial loop
remain incomplete.
