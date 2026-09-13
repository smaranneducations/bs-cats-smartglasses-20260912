# Canonical publishing operations

One governed 9:16 video lasting 30 to 90 seconds becomes one immutable distribution package. It pins the video, poster, optional captions, one primary ontology concept, at most two products, channel copy, disclosures, evidence, media rights and destinations.

The audience composer now creates one-attribute cards and one atomic card per video plan. The audience app prefers approved self-hosted videos and records interactions against the distribution package. Legacy cards remain a fallback until a video is approved and staged.

## Prepare without publishing

Create and review the render and release-review packet, then run:

```bash
python3 scripts/prepare_distribution_package.py <render-artifact-id> --concept <ontology-concept-key>
```

This creates a `distribution_package`, a pending `publication_request`, a local poster when needed and manual Instagram, TikTok and X kits. It performs no upload.

## Approve and execute

Review the exact video, copy, disclosure, evidence, rights and destinations. Approve the `publication_request`. Any hash or version change blocks execution.

For one approved run, locally set `ALLOW_APPROVED_PUBLICATION=1`, then run:

```bash
python3 scripts/publish_approved_package.py <publication-request-id>
```

An approved subset can be selected with repeated `--destination` arguments. Unapproved destinations cannot be added.

Local configuration:

- `PUBLIC_APP_BASE_URL`: deployed app origin; preparation defaults to the local app.
- `YOUTUBE_OAUTH_ACCESS_TOKEN` or `YOUTUBE_OAUTH_TOKEN_FILE`: OAuth with upload permission.
- `YOUTUBE_PRIVACY_STATUS`: defaults to `private`.
- `YOUTUBE_CATEGORY_ID`: defaults to Science & Technology (`28`).
- `LINKEDIN_ACCESS_TOKEN` or `LINKEDIN_OAUTH_TOKEN_FILE`: authorized LinkedIn token.
- `LINKEDIN_PERSON_URN`: approved member or organization author.
- `LINKEDIN_API_VERSION`: defaults to `202608` and must be reviewed when versions retire.

The owned-app adapter retains the exact video and poster. YouTube uses resumable upload. LinkedIn uses Videos API upload/finalization and Posts API publication. Instagram, TikTok and X receive manual kits pointing to the same video and app link.

Credentials are read only inside publisher adapters and are never written to receipts. Provider rejection or ambiguous delivery is recorded and is not retried blindly. Code readiness does not prove OAuth scope, platform eligibility or deployment state.
