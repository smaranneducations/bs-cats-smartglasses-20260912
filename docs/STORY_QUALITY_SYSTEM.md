# Story quality system

Status: the deterministic story-structure gate is implemented for new storyboards. Strong-model scoring is specified and required before release-candidate status, but its production executor is not yet connected. Exact-artifact human approval remains mandatory for publication.

## Why visual polish is insufficient

A safe source-linked video can still be forgettable. Colour, music, motion and product photography are presentation tools; they do not create a reason to care. The narrative must reveal a useful difference, trade-off, change or insight and connect it to a real audience consequence.

The system therefore separates analysis, direction, composition and rendering. The analyst establishes defensible decision levers. A task-scoped story director uses a strong reasoning model only for the high-leverage narrative decision. The composer executes the pinned strategy. Deterministic code validates structure and lineage, and the renderer reproduces pinned bytes and assets.

## Required arc

Every new storyboard must contain these five ordered roles:

1. `hook`: earn attention within eight seconds using audience tension or a consequential question.
2. `tension`: explain why the obvious answer or default assumption is incomplete.
3. `differentiator_and_proof`: reveal one source-bound decision lever with its comparison basis and caveats.
4. `implication`: translate that lever into what changes for the intended audience.
5. `payoff`: resolve the opening tension with a memorable decision or next action.

At least four distinct visual primitives are required. Primitive variety alone does not earn quality credit; every primitive needs a distinct narrative function.

## What counts as differentiation

A differentiator may be a product difference, technology trade-off, audience fit, ecosystem dependency, market change, regulatory consequence, evidence gap or other defensible insight. It must be useful to the selected audience and linked to governed assertions.

If a product or subject name can be replaced while the story remains materially unchanged, the candidate is generic. If no valid decision lever exists, the director returns the brief for bounded evidence or chooses a different story family. It never invents superiority, urgency, hands-on experience or novelty.

## Quality assessment

[`config/story-quality-policy.json`](../config/story-quality-policy.json) defines a 100-point rubric covering hook and curiosity, audience relevance, decision-relevant differentiation, evidence, visual progression and payoff. The minimum candidate score is 80, with one initial direction attempt and at most one repair.

Scoring does not override hard failures or governance gates. Deterministic checks can establish that required fields, ordered beats and evidence references exist; they cannot truthfully establish whether a viewer feels excitement. Strong-model evaluation and the exact-artifact human review cover that remaining judgment without sending every data record to a human.

## Measurement and learning

Creative review records hook clarity, felt relevance, remembered differentiator, trust, desire to continue and confusion. Once published, three-second hold, completion, rewatch, save or share, qualified click and useful comments become evidence for revisions.

No single engagement metric is the objective. A sensational story that loses trust or attracts no useful audience is a failure. Optimization balances qualified audience value, editorial trust, human effort, variable cost and contribution.

## Runtime boundary

New storyboards now carry a typed `story_strategy`, five semantic scene roles and a `creative_gate`. The planner revalidates this contract before preparing an image-led render recipe. Legacy private storyboards remain readable but do not silently gain release-candidate status.

The remaining implementation is to connect the strong-model story-director executor, persist dimension reasons and evaluation cases, and make the release controller verify an accepted score before creating a release candidate. Until that exists, a structurally valid private preview is not evidence that the storytelling itself passed the complete quality system.
