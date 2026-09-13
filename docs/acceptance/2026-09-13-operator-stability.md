# Post-login operator acceptance correction

Governing issue: #36. This records a separate defect discovered only after hosted Google authentication succeeded.

## Problem statement
The signed-in administrator could not use the workspace because its page stopped responding.

## Issue identified
The session and protected workflow/data APIs returned HTTP 200, but the loading workspace repeatedly inserted itself into the DOM.

## Root cause
The catalogue-loading/error placeholder lacked the stable ID used by its MutationObserver guard. Each insertion triggered another insertion before asynchronous work could complete.

## Key steps
Give every workspace state one stable mount identity, synchronize hash navigation, and align JSON writes with the existing API contract and authenticated actor attribution.
Add regression cases for observer stability, loading/failure/success, navigation, request headers and error propagation. Actual results and deployment receipts follow execution; this document alone is not an acceptance pass.

## Risk and rollback
No administrator permission, data-store or publication-gate changes. Revert the scoped controller patch and redeploy the preceding recorded Hosting artifact if the change causes a regression.

## Cache consistency follow-up

The Hosting builder now adds a content-derived version to each owned entrypoint script and stylesheet URL. Existing query parameters, fragments and external assets are preserved; missing or escaped local paths fail the build. Seven regression cases cover version changes, repeatability, browser-relative paths and isolation. This prevents mixing a new document with an older browser-cached bundle; it is not a substitute for live browser acceptance.

## Managed branch state follow-up

Hosted inspection reached the authenticated eight-stage workflow and the 27-concept ontology. Clicking a managed dataset branch then raised a null-view error: the hash handler cleared view state, but an existing DOM mount caused initialization to return early. Initialize state before reusing a mount and make branch selection establish its own validated stage/type. Six regression cases cover this event ordering, recovery, unknown branches and creative/learning navigation.

### Filter visibility regression

Hosted Chrome testing showed filtered records were still visible because the author-level grid display overrode the native hidden attribute. The record grid now explicitly respects hidden rows, reports the visible count and presents a no-results state.

Validation: all 215 Python tests and 45 JavaScript tests passed; the Hosting builder produced 43 files. Hosted verification follows deployment; this result does not imply that every authenticated write or publishing workflow has passed.
