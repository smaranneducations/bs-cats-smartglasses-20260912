# Media catalog and generation fallback

## Reuse-first rule

Every agent must resolve image requests through the shared catalog. A request identifies its subject, scene, purpose, style, aspect ratio, required tags, publication intent and whether exact product identity is required. The resolver rejects an otherwise similar asset when its rights or depiction limits do not fit the requested use.

The catalog stores SHA-256 byte identity, workspace path, dimensions, provenance, creator/source/license, rights state, commercial-use state, representation type, product-photography warning, depiction limits, semantic tags, generation model and prompt hash, cost, creation time and reuse history. Re-registering identical bytes updates the same record rather than creating a duplicate.

Downloaded Commons images and legacy private-preview images enter this catalog through their existing acquisition or planning path. Generated images are stored under assets/media/generated/<sha256>/ with a metadata sidecar and are also registered as governed media assets.

## Gemini fallback

Generation is allowed only after catalog reuse and lawful acquisition fail. The default stable model is gemini-2.5-flash-image at 1024px. Google's price observed on 2026-09-13 is USD 0.039 per output image, plus a small text-input charge; the project reserves a conservative USD 0.05 estimate and rejects any complete request estimated above USD 0.10.

Pricing must be refreshed after 2026-10-13. A stale price, unreconciled project costs, disabled paid execution or unavailable shared reservation blocks generation. The cap is a maximum, not a target or separate budget.

The provider call permits one output image and one attempt. Network timeout or an ambiguous response is recorded as potentially billable and is never retried automatically. A different request needs a new idempotency key and fresh admission.

Generated output is an original conceptual illustration, never evidence of a named product's appearance, feature or camera quality. Prompts prohibit logos, trademarks and embedded text. The resulting asset remains a private-preview candidate until visual, rights, factual and exact-artifact publication review pass.

Official pricing: https://ai.google.dev/gemini-api/docs/pricing

Official image-generation guide: https://ai.google.dev/gemini-api/docs/image-generation
