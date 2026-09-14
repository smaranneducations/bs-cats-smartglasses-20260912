# Product-history index repair

## Problem statement
Hosted product inspection and comparison must use attributable version history, not just display a form that cannot load its evidence.

## Issue identified
Chrome reached both forms, but their API calls returned "Object store failure." The same read-only comparison failed against the real Firestore store.

## Root cause
The history query filters `governed_object_versions.object_id` and orders by `version`; the deployed composite-index list was empty. In-memory test transports did not enforce Firestore index requirements.

## Key fix steps
Declare the exact collection-scoped index in `firestore.indexes.json`, retaining payload-index exemptions and all access controls. Test the query/index contract, deploy the index, wait for readiness and repeat the hosted product/comparison flow.

## Acceptance boundary
Unit success is not production acceptance. Record the real index readiness and browser outcomes in the linked GitHub change; private video-storage permissions and exact-artifact publication remain separate gates.
