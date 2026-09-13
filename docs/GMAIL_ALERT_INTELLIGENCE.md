# Gmail Alert intelligence

## Operating role

Google Alerts is a discovery inbox, not the evidence warehouse. The pipeline reads only messages matching the configured SmartGlasses alert query. It extracts external article links, records minimal idempotency receipts and creates one compact dated market observation.

It does not store full email bodies, attachments, unrelated mail, contact data or credentials. It does not copy full articles. Before any article contributes factual claims, a separate source-policy and credibility workflow must examine the original source.

## Authentication

The Gmail API is enabled on the SmartGlasses Google Cloud project. Authentication uses the read-only gmail.readonly OAuth scope. SMTP and Gmail app passwords are not used.

Run the one-time consent setup:

    python3 scripts/setup_gmail_oauth.py

The script opens Google's consent page because account-holder consent cannot be completed through an API. After consent, the refresh token is stored only at .local/gmail-alerts/oauth-token.json with file mode 0600.

The script prefers GMAIL_OAUTH_CLIENT_ID and GMAIL_OAUTH_CLIENT_SECRET. When blank, it can reuse the locally configured Google Drive OAuth client. No client secret or token is printed.

## Incremental ingestion

Run:

    python3 scripts/run_gmail_alert_ingest.py

The local database deduplicates both Gmail message IDs and SHA-256 fingerprints of canonical article URLs. Repeated alerts update last-seen and occurrence counts rather than creating duplicate articles. The governed object store receives one run-level market observation, not one approval item per link.

The next source-research stage will turn admitted articles into versioned sources and clustered dated news events. Those event objects can support hot-news cards, short videos, blog drafts, monthly digests and later multi-month trend reports. Exact publication remains a human decision.

## Security action

Any Gmail app password previously pasted into chat must be considered exposed and replaced before SMTP sending is enabled. Revocation should be coordinated so another project is not silently broken.
