# First $500 experiment: budget and success scorecard

Version 1.1, 2026-09-13. Financial-owner instruction: include subscriptions, APIs, hosting and all other project costs. USD is the planning currency assumed from reported dollar amounts.

The next decision is D0 in `.local/governance/DATA_FIT_DECISION_2026-09-13.md`, followed by the selected domain's H1 acceptance contract. This may change the first commercial subject, not the cumulative budget, quality gates or requirement to demonstrate demand. Planning and a playable demo are not a complete operational platform.

## The decision this experiment must support

Determine whether a small reusable domain-intelligence system helps its human operator curate and commercialize useful knowledge, using SmartGlasses as the first domain. Validate both the operator workflow and whether its evidence-led outputs attract people who return and show genuine buying interest, at sustainable cost and workload. Views and website traffic are useful early signals. They cannot by themselves establish a viable platform or business.

The objective is to learn this before the $500 ceiling is reached. We are not required to spend $500. A useful pipeline is delivery success; audience and intent are validation signals; collected revenue and repeatable positive contribution are business evidence. Report these separately.

## Current budget

| Item | Amount | Evidence |
| --- | --- | --- |
| Total cumulative experiment ceiling | $500 | Explicit owner instruction, 2026-09-12 |
| Subscription paid today | $80 | Owner-reported payment; invoice not inspected |
| Maximum remaining before all other costs | $420 | Arithmetic ceiling, not verified spendable cash |
| Other API, cloud and renewal exposure | Unknown | Needs source reconciliation |
| Protected buffer for delayed/fixed charges | $50 | Operator control within the $500 ceiling |

Every project expense belongs in this envelope. Charge the reported subscription amount once; included model usage does not add a second subscription expense. If the owner later pays for a $200 plan, record the actual charge, date and any verified credit/proration. Do not assume that $200 replaces $80 or that mentioning the plan authorizes a purchase. Renewals consume the same experiment allowance.

Keep invoices, receipts, raw billing exports and private analytics outside public Git history. Store only the minimum non-sensitive project summaries needed for decisions. Preserve original currency and the exchange-rate evidence for conversion; do not silently treat CHF or EUR as USD.

Maintain distinct ledger states for paid invoices, accrued/unbilled usage, outstanding job reservations and committed future charges. Reconcile overlapping items by provider, period and transaction/job reference so an invoice replaces the corresponding estimate instead of doubling it. Include taxes/fees where charged. Provider-wide bills shared with other projects need task/project attribution; do not charge every shared account cost to this project automatically.

`Total exposure = recorded experiment costs + non-overlapping unbilled estimates + live reservations + committed upcoming costs`.

`New-work headroom = max(0, $450 - total exposure)`, but only after the components are reconciled and current. Unknown cost is not zero. $500 is the outer ceiling; $450 is the internal admission stop. The buffer reduces risk but does not make delayed provider accounting or persistent costs disappear.

## Staged spending decisions

| Exposure checkpoint | Required review | Operating response |
| --- | --- | --- |
| $150 | Does one useful grounded video work, or is foundation effort consuming the experiment? | Cut scope or change the approach if there is no usable output; avoid more infrastructure |
| $250 | Is publication/measurement live and is the first audience evidence being collected? | Fix distribution or instrumentation before producing a larger backlog |
| $350 | Are people returning, asking meaningful questions or discussing a paid use case? | Concentrate remaining work on the strongest evidence; avoid automatic scale-up |
| $450 | Produce the experiment decision report and inspect upcoming fixed/late charges | Stop admitting new paid work; protect the remaining $50 |
| $500 outer ceiling | No further expense is authorized | No automatic top-up, budget reset or recycling of revenue into new spend |

Use $2 per variable-cost job and $5 per day as initial internal limits, subject to the tighter remaining total. These are design rules until the shared admission ledger is implemented and tested. Existing jobs, storage and subscriptions require separate reconciliation. Local development can continue while paid work is unarmed.

## What we will measure

| Dimension | Measurement | Interpretation |
| --- | --- | --- |
| Core platform | Object-level context form, semantic definitions, agent proposal, human decision, history and reuse across two output types | Does human expertise combine with governed agents in a reusable workflow? |
| Useful output | Original videos, evidence pages, claim coverage, correction rate and successful publication | Did the core system deliver something reliable to an audience? |
| Reach | Video views by format, Shorts engaged views separately, website users and source of visits | Are people discovering it organically? |
| Attention | Watch time, average viewing percentage/duration, engaged website sessions, comparison/evidence actions | Is the material useful enough to consume? |
| Return | Returning viewers/users where available; repeated qualified interactions | Does value persist beyond a single click? |
| Intent | Explicit interest in a comparison/research service, a specific problem described, offer inquiries | Is there a plausible paying need? |
| Revenue | Collected payments; platform estimates reported separately; refunds and fees | Has anyone actually paid, and what contribution remains? |
| Efficiency | Variable cost per accepted video, total experiment cost per qualified inquiry, review minutes and failure/retry cost | Can the process be sustained by one owner? |

Record observation window, content/video ID, source, retrieval time, metric definition and availability status for every snapshot. Exclude known owner testing and bot traffic; avoid claiming perfect bot exclusion. Do not add YouTube viewers and website users together as if they were deduplicated people. Use video-specific tagged links for attribution and report its limitations.

Compare videos over matched age windows, such as their first seven complete days, and keep Shorts separate from ordinary video measures. Use 28-day windows for broader audience reviews. Wait for reporting lag. Do not confuse missing metrics, suppressed data or a permission error with zero audience.

## Initial targets and how to decide

These are our initial experiment targets, not industry benchmarks, platform eligibility rules or promised outcomes. Set them before seeing results and keep any later revision explicit with a reason. Early small samples remain weak evidence.

1. Core delivery target: demonstrate human-added context through an object form, a governed agent proposal, an attributable review decision, semantic evidence/history, and reuse of approved knowledge in both a comparison/report and an explainer. Include one fully traced research-to-publication-to-metrics run and one metadata-driven field addition. Aim for six distinct published videos with accompanying evidence pages during the audience experiment; video count is a secondary target and cannot replace the core workflow. Every factual claim needs evidence; major known errors block publication.
2. Exposure target: at least 28 days of observation after the first publication, plus either 1,000 ordinary-video views, 2,000 Shorts engaged views, or 100 engaged website users. Report which branch was met. Views should be distributed across at least three videos when a video branch is used. This only makes the audience experiment interpretable; it is not profitability.
3. Repeat/intent target: observable returning audience or recurring useful interactions across two weeks, and at least five distinct independent people expressing a specific use case or commercial interest, including two willing to discuss an actual offer and price. Likes alone are not qualified intent.
4. Business-evidence target: seek one genuine paid pilot or verified platform/affiliate receipts, with attributable delivery costs. A first payment is preliminary validation; sustainable success needs repeated positive contribution and demand, not one transaction.
5. Efficiency target: aim for no more than $5 variable production cost and ten owner review minutes per accepted video across the latest three pieces. These exclude one-time development but must be shown beside full experiment burn. Reduce scope if the process cannot approach those targets.

If fewer than 28 observable days are available before the budget stop, report insufficient evidence and stop new paid work anyway. Do not buy more exposure merely to make a score green.

The experiment report uses three separate judgments:

- Continue cautiously: the delivery target is met, multiple pieces show repeat/intent evidence, and there is a credible offer or first payment with manageable costs. Recommend a specific next experiment; another budget still needs owner authorization.
- Improve or narrow: work is useful but distribution, attention, intent or cost is weak. Identify the failed stage and propose a low-cost correction. High views with no relevant actions do not justify scaling.
- Not validated: the budget boundary arrives with insufficient useful output or demand evidence. Preserve the reusable assets, explain what was learned and pause paid production. An absence of adequate data should be labeled inconclusive rather than proof that no market exists.

Positive recurring operating surplus is the eventual business success criterion. Record operator time saved, independently completed workflows and repeated use alongside audience metrics. Demonstrating Bhasker's own workflow does not prove that other founders will pay for the platform; that requires a separate customer test later. YouTube monetization eligibility and approval must be checked for the actual channel; reaching these experiment targets does not make it eligible. [YouTube Partner Program](https://support.google.com/youtube/answer/72851).

## Data collection with minimal owner work

Use authenticated APIs first, a saved CSV export second, and a scoped read-only browser inspection third. A screenshot can support a manual observation but is less convenient for repeated comparisons. Never read unrelated accounts or capture secrets. Preserve date range, metric label, units and collection method when transcribing a chart. Avoid keeping private screenshots in the public repository.

YouTube channel analytics requires the channel owner's consent. The read-only analytics scope provides activity reports; monetary reports additionally require the monetary scope and an eligible monetized channel. Upload credentials alone do not establish analytics access. Start with the activity reports and request monetary access only when useful. [YouTube Analytics channel reports](https://developers.google.com/youtube/analytics/channel_reports).

Use supported views, watch time, viewing duration/percentage and subscriber metrics according to each report's definitions. Keep estimated platform revenue separate from paid receipts because estimates can change. Returning-audience or other Studio-only figures may require a documented manual/export path where no supported API report exists. [YouTube metric definitions](https://developers.google.com/youtube/analytics/metrics).

For the website, add minimal consent-aware event measurement and exclude owner testing. After the property and access are configured, use the Google Analytics Data API for supported reports and registered events, such as meaningful comparison use or an inquiry submission. The API reads collected data; it does not create website instrumentation by itself. [Google Analytics Data API](https://developers.google.com/analytics/devguides/reporting/data/v1).

For costs, use available project/provider usage and billing reports, plus the application's request ledger. Do not assume every provider exposes current spend through an API. Ask the owner only for otherwise unavailable actual payment amount/date or a scoped export. Reconcile API estimates against settled invoices; preserve missing data honestly.

The app usage tool currently reported 99% of the main weekly allowance remaining on 2026-09-12. It cannot tell us exactly how many Astra hours remain; task size, reasoning and model choice affect usage. The snapshot is not a charge or a forecast. Use economical models for bounded work and check usage when relevant. Subscription and API usage have different charging mechanisms. [OpenAI usage and pricing](https://learn.chatgpt.com/docs/pricing).

These measurement integrations are planned, not connected by this scorecard. No channel, website or provider-spend data has been automatically imported during this planning step.

## Trust positioning and decision-engine learning

Treat "Evidence over hype" as a testable positioning choice, not a monetization veto or proof of uniqueness. Learn from a small set of distinct outputs whether clear limitations and decision-focused evidence help people understand, return, compare or inquire. Every presentation variant must retain honest claims and required disclosures. Small-sample differences are directional, not causal proof or permission to scale.

Report factual claim coverage, material corrections and correction propagation separately from attention, intent, actual revenue, production cost and human minutes. Additional research must resolve a decision-relevant uncertainty. Respect each platform's metric definitions and permitted use; do not invent incompatible composite platform scores.

Measure the intelligence loop through time from useful feedback to a justified decision, reusable changes passing applicable evaluations, repeated failures, regressions/rollbacks and cost per accepted result. Record unknowns until instrumented. Less repeated error and unnecessary reasoning is better evidence of learning than more agents, rules or stored feedback.

For D0, compare lawful data/media coverage, variant accuracy, refresh burden, human effort and attainable commercial use cases before choosing a domain. A larger data catalogue or a list of potential sponsors does not establish demand or revenue. These measures are planned, not integrations activated by this review.

## Daily financial-owner view

Show known cost, estimated total exposure, unknown charges, next billing commitment, allowance status, useful output, audience/intent evidence and the next decision. Bhasker supplies payment amounts only when no authorized source exists, helps validate an ambiguous metric when necessary, and reviews the actual artifacts. Routine collection and analysis belong to the implementation agent.
