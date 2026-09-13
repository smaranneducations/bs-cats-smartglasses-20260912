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
