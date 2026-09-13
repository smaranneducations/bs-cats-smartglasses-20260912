# YouTube market-learning pipeline

## Purpose

This workflow uses a small, repeatable set of public YouTube Data API searches to find channels that repeatedly publish about SmartGlasses. They are candidate research inputs, not a definitive ranking, endorsement list or substitute for product evidence.

The workflow learns only from current titles and description metadata. It does not download or retain video, audio, thumbnails, transcripts, comments, viewer identity, subscriber counts or channel statistics. Product claims still require the platform's governed source and factual-review workflow.

## Monthly operation

Run the following command:

    python3 scripts/run_youtube_market_learning.py

The scheduled job runs every four weeks. That interval approximates a monthly cycle while keeping the current metadata snapshot within its 29-day lifetime. Re-running an already completed cycle returns its receipt instead of capturing duplicates.

The workflow uses YOUTUBE_API_KEY from the ignored local .env. It does not print the key, ask for YouTube-account access or use the upload credential. Six bounded searches are the default; no paid model call is admitted.

## Records and deduplication

Ignored local state is stored under .local/youtube-market-learning/ with mode 0600 files:

- current-snapshot.json contains only the current candidate channel/video metadata and an explicit expiry.
- runs/YYYY-MM.json stores only our operational request/result counts and one snapshot fingerprint; it stores no video IDs, channel IDs, titles or descriptions.

The pipeline deduplicates by YouTube video ID only within the current unexpired snapshot, then fingerprints normalized current metadata to distinguish new, changed and unchanged observations. The current snapshot is overwritten and expired snapshots are removed before use. This deliberately limits historical deduplication so non-authorized API metadata is deleted or refreshed before 30 days.

## Learning outputs

Each successful cycle creates an expiring private snapshot and a metadata-free operational receipt. Topic counts and ontology signals remain inside the expiring snapshot. They can guide current research, but they cannot become permanent feedback, ontology or product facts until independently corroborated through the governed evidence workflow.

Potential schema gaps need multiple distinct videos and channels before one batched ontology proposal is created. The pipeline never activates a field or writes a product value. monthly_subscription and app_ecosystem are already first-class ontology definitions because the operator explicitly identified those missing comparison dimensions.

## Adoption decision

EfficientStreet/youtube-subscriptions-ingest is MIT-licensed and informed the incremental-ID deduplication and raw-to-knowledge separation. Its authenticated-subscription importer and transcript stage were not copied or installed: personal subscriptions do not discover the wider market, and transcript scraping would introduce unnecessary access, rights and platform-policy risk.

Repository: https://github.com/EfficientStreet/youtube-subscriptions-ingest

Current implementation follows the official YouTube API Services Developer Policies and YouTube Terms of Service. Provider rules can change; the scheduled workflow must fail closed if its policy assumptions are no longer current.

Policies: https://developers.google.com/youtube/terms/developer-policies

Terms: https://www.youtube.com/t/terms
