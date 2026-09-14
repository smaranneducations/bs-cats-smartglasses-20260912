# Hosted workflow validation: 2026-09-14

## Live application

- [Administrator workflow](https://bs-cats-smartglasses-20260912.web.app/operator)
- [Audience application](https://bs-cats-smartglasses-20260912.web.app/discover)
- [Comparison and navigation repair: PR 45](https://github.com/smaranneducations/bs-cats-smartglasses-20260912/pull/45)
- [Product-history index repair: PR 46](https://github.com/smaranneducations/bs-cats-smartglasses-20260912/pull/46)
- [Overall acceptance remains open: issue 36](https://github.com/smaranneducations/bs-cats-smartglasses-20260912/issues/36)

This is a verified partial acceptance record, not a claim that the complete business vision or every integration is operational.

## Actual checks

| Area | Observed result |
| --- | --- |
| Regression suite | 242 Python tests and 53 JavaScript tests passed on the combined maintenance branch. |
| Hosting | 47-file build deployed; Chrome renders the styled operator and audience pages. |
| Google authentication | Signed out, reloaded and completed a fresh Google sign-in on the production operator. |
| Data access boundary | Ten hosted HTTP checks passed: public surfaces return 200; protected session, workflow, ontology, preview and media-list endpoints return 401 anonymously. |
| Administrator feedback | The previously created test feedback record remained at version 2 after reload and sign-in; create/update persistence was accepted in the preceding maintenance receipt. |
| Comparison controls | All 27 registered concepts are offered; selecting fewer than two products is rejected clearly. |
| Comparison execution | Chrome compared VITURE Luma Pro and RayNeo Air 4 Pro using real Firestore data, including values, conditions, dates and market/variant caveats. |
| Unknown values | Recurring subscription and app ecosystem remain "Not available" where evidence is absent; no false values or automatic winner were fabricated. |
| Product inspection | The product link opens an authenticated in-operator evidence table with object version, source link and field conditions. |
| Public comparison | Opens without entering administrator pages; explains that two published products are not yet available. No unpublished product records are exposed. |
| Public navigation and sources | Discover, comparison and the image/source disclosure panel were exercised in Chrome. |
| Private review navigation | The old review URL redirects to the operator. Its authenticated dialog loads the correct draft identity and metadata. |
| Private video playback | NOT accepted: the dialog reports "Private artifact file is unavailable." Cloud asset access has not been granted and drafts were not uploaded during this repair. |

## Problem statement
The hosted experience must execute real evidence workflows, not merely display forms. Source history, media privacy and publication controls must survive deployment.

## Issues identified
Comparison choices and legacy navigation were fragmented; product inspection/comparison failed against the real cloud store. Local draft paths also cannot serve hosted video files.

## Root causes
The comparison UI did not expose the full ontology, and legacy protected destinations relied on navigation without the application's authentication transport. Firestore history required a composite index absent from deployment configuration; private render storage remained local.

## Key fix steps
Integrate comparison and inspection into the operator, separate published-only audience evidence, and preserve authenticated media transport. Deploy the exact product/version history index and repeat the real query and Chrome workflow after it reaches READY.

## Deployment and recovery
The history index reached READY, and both the real-store comparison and browser result passed. The new backend revision was promoted only after that failure was resolved; the temporary candidate route was then removed and the previous revision retained for rollback.

The index is version-controlled in `firestore.indexes.json`; keep it when rolling application code backward. Detailed private maintenance provenance remains in the existing private repair record rather than this public document.

## Remaining gates and next steps

- Obtain explicit permission for the existing app service to read the project's private asset bucket. The access change was blocked by the execution safety review; no alternate sharing mechanism was used to bypass it.
- After permission, upload only manifest-pinned governed drafts privately, configure the existing media adapter and test authenticated playback, hashes, byte limits and anonymous denial. Do not upload local credentials, unrelated assets or unapproved content to public hosting.
- Verify the production media-probe dependency and the exact release checks; passing a local renderer test does not establish hosted render or publication readiness.
- Retain rights, factual and exact-artifact approval gates. Three visible drafts are not yet cleared for publication; neither their metadata nor this receipt authorizes posting to social accounts.
- Public engagement, durable cloud task execution and the complete research-to-publication-to-revenue loop remain outside accepted production coverage. Do not describe an editable agent roster as proof that all those agents run autonomously.
- Continue tracking these gaps in issue 36. Keep published-only public views truthful and do not fill the feed with private drafts merely to make testing look complete.

## Cost and privacy
No model-generation or social-publishing call was made for this repair; no paid service, instance limit or spending ceiling was added. Provider request, index-storage and deployment charges are not reconciled here and must not be represented as zero.

No provider credentials, private record exports or account tokens belong in this receipt. Existing authentication, private-media boundaries and publication authority remain unchanged.
