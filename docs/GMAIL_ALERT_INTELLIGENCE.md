# Gmail Alert intelligence

## Operating role

Google Alerts is one discovery adapter, not the evidence warehouse or a single point of availability. The pipeline reads only messages matching the configured SmartGlasses alert query. It extracts external article links, records minimal idempotency receipts, creates separate deduplicated `news_discovery_item` objects and creates one compact dated run observation.

It does not store full email bodies, attachments, unrelated mail, contact data or credentials. It does not copy full articles. Before any article contributes factual claims, a separate source-policy and credibility workflow must examine the original source.

## Authentication

The Gmail API is enabled on the SmartGlasses Google Cloud project. Authentication uses the read-only gmail.readonly OAuth scope. SMTP and Gmail app passwords are not used.

Run the one-time consent setup:

    python3 scripts/setup_gmail_oauth.py

The script opens Google's consent page because account-holder consent cannot be completed through an API. After consent, the refresh token is stored only at .local/gmail-alerts/oauth-token.json with file mode 0600.

The script prefers GMAIL_OAUTH_CLIENT_ID and GMAIL_OAUTH_CLIENT_SECRET. A dedicated Gmail OAuth client is the safest configuration; the fallback client remains a migration convenience. Incremental scope combination is disabled, and the helper refuses to store a token unless Google returns exactly `gmail.readonly`. No client secret or token is printed.

The previously stored token is currently unsuitable because it combines Gmail read access with YouTube upload scopes. Do not weaken the client check. Run the consent setup again after this change. If Google still returns a combined grant, create a Gmail-specific OAuth client or revoke the prior combined grant before retrying; coordinate revocation so an unrelated integration is not broken.

To diagnose delivery without reading message bodies or saving message identifiers:

    .venv/bin/python scripts/run_gmail_alert_ingest.py --diagnose-only

The diagnostic reports aggregate counts for the configured query in the inbox, the same query including spam/trash, and Google Alert sender visibility. It distinguishes no delivery from filtering or topic-query mismatch without scanning unrelated personal mail.

## Incremental ingestion

Run:

    python3 scripts/run_gmail_alert_ingest.py

The local database deduplicates both Gmail message IDs and SHA-256 fingerprints of canonical article URLs. Repeated alerts update last-seen and occurrence counts rather than creating duplicate articles. A durable local outbox ensures a stored article can still create its governed discovery object after an interrupted object-store write. Opaque Gmail message IDs are hashed before entering request audit data.

Each new article URL becomes a `news_discovery_item` with `discovery_only` evidence state, `unclustered` event state and blocked video eligibility. These items are operational work, not human review requests.

The next source-research stage turns admitted articles into versioned sources and clusters genuinely related coverage into dated `industry_event` context objects. Only then can a story director create a current-event video candidate using the same hook, differentiator, proof, implication and payoff gates as other videos. Those events can also support hot-news cards, blog drafts, monthly digests and later multi-month trend reports. Exact publication remains a human decision.

Approved direct sources, lawful feeds and bounded web research can later emit the same discovery contract. This keeps the world-events dataset alive when Google sends no alerts without treating search results, snippets or copied articles as evidence.

## Security action

Any Gmail app password previously pasted into chat must be considered exposed and replaced before SMTP sending is enabled. Revocation should be coordinated so another project is not silently broken.
