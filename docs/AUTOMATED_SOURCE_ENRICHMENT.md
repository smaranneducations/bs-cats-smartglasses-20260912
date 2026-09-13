# Automated source enrichment

## Decision

Google Alerts is an optional email discovery adapter, not the news backbone. Google documents Alerts as a consumer email feature and does not publish a Google Search Alerts API. The platform therefore uses direct authoritative feeds, GDELT and bounded search providers to keep working when Alert emails are delayed or absent.

Search APIs only locate candidate URLs. Their snippets never become evidence. A later source-admission stage must fetch the originating page, check access and reuse rights, classify source authority and freshness, extract a candidate assertion, normalize it through the ontology and preserve its lineage.

## Routing order

1. Reuse an admitted cached source that is still fresh.
2. Read configured manufacturer, regulator, standards-body or newsroom RSS/Atom feeds.
3. Use GDELT for news, regulation and market-context discovery.
4. Use Tavily for a bounded agent-oriented second sweep.
5. Use Exa for semantic and ontology research.
6. Use Serper for Google-specific precision coverage.
7. Use Brave for independent-index confirmation.
8. Consider DataForSEO only after the free-provider benchmark justifies its minimum deposit.
9. Keep Reddit disabled until explicit written commercial approval and deletion compliance exist.

The executable policy is `config/workflows/source-enrichment.json`. It caps requests, estimated cost, providers per task, response size and retries. The local ledger stores only canonical candidate URLs and hashes, not search snippets or complete response bodies.

## Run modes

Create a private task from `config/source-enrichment-task.example.json`, then inspect the plan without making network calls:

    python3 scripts/run_source_enrichment.py .local/source-enrichment/my-task.json

Run only configured no-charge adapters:

    python3 scripts/run_source_enrichment.py .local/source-enrichment/my-task.json --execute-free

Metered providers require a configured local credential and an explicit bounded invocation:

    python3 scripts/run_source_enrichment.py .local/source-enrichment/my-task.json --allow-paid

The command performs no automatic retry. A recent identical provider query is suppressed for 30 days. Paid requests stop at USD 0.10 per task and USD 1.00 per run, within the stricter shared experiment limits.

## Local credential fields

Credentials stay in ignored `.env`; never paste them into chat, issues, commits or logs.

| Field | Purpose | Initial decision |
| --- | --- | --- |
| `TAVILY_API_KEY` | Agent-oriented web discovery | Recommended first free benchmark |
| `EXA_API_KEY` | Semantic and ontology discovery | Recommended free benchmark |
| `SERPER_API_KEY` | Google SERP discovery | Recommended free benchmark |
| `BRAVE_SEARCH_API_KEY` | Independent-index discovery | Optional benchmark |
| `DATAFORSEO_LOGIN` | Deferred bulk SERP account | Leave blank initially |
| `DATAFORSEO_PASSWORD` | Deferred bulk SERP password | Leave blank initially |
| `REDDIT_CLIENT_ID` | Approved Reddit application | Leave blank and disabled |
| `REDDIT_CLIENT_SECRET` | Approved Reddit application | Leave blank and disabled |
| `REDDIT_USER_AGENT` | Transparent approved Reddit client | Leave blank and disabled |

Provider account creation and acceptance of provider terms remain account-holder actions. No paid package, automatic top-up or commercial Reddit access is authorized by placing a field in the template.

## Google Alerts and Gmail

Google Alerts can only send matching results through its configured delivery method. The Gmail API reads those messages but cannot create, repair or force Google Search Alerts.

Use Google's own troubleshooting sequence first: verify the signed-in account, ensure the alert is enabled, check its frequency/source/language/region/result settings, inspect spam, and add `googlealerts-noreply@google.com` to contacts. Then run the privacy-preserving local diagnosis:

    .venv/bin/python scripts/run_gmail_alert_ingest.py --diagnose-only

The Gmail path needs a dedicated OAuth client ID and secret in `.env`, followed by one interactive read-only consent:

    python3 scripts/setup_gmail_oauth.py

The resulting refresh token is stored at `.local/gmail-alerts/oauth-token.json` with mode `0600`. SMTP credentials cannot read inbox messages and are not used.

## Acceptance metrics

- Cost per accepted useful assertion, including extraction and review.
- Percentage of missing fields resolved from admitted primary sources.
- Incorrect-candidate and contradiction rate.
- Duplicate-query suppression rate.
- Human minutes per accepted assertion.
- Staleness and refresh success by attribute class.
- Percentage of discovery candidates rejected for access, rights or credibility reasons.
