# Governed context photographs

**Current integration status, 2026-09-13:** acquisition and authenticated asset
registration were exercised, and all 11 focused importer checks passed. Two
visually inspected CC0 candidates and a separate recipe were captured. The
existing renderer correctly rejected that recipe because this importer writes to
`assets/media/commons`, outside the admitted image directory
`.local/assets/kinetic`. No new context variant was rendered and no allowlist was
widened. Directory alignment is a disclosed correction awaiting the human's
repair decision. These images are not yet usable through the admitted renderer.

This route acquires a small set of creator-uploaded CC0 photographs to illustrate
context. It does not obtain product-photo rights, validate a device's appearance,
or establish what a device camera or display produces.

`scripts/import_commons_context.py acquire` uses the public Wikimedia API for at
most three explicit file titles. It requires the file-level CC0 declaration, its
licence URL, a named creator, an own-work record and no stated extra restrictions.
It does not mistake Commons' general structured-data licence for an image licence.
Only small JPEGs from the returned Wikimedia media hosts are accepted, with
redirects disabled and byte/pixel limits checked. Original large files are not
downloaded. Source metadata, revision, observation time and content hashes are
retained alongside the image.

An agent must inspect the downloaded image before registration and supply a
specific visual-risk assessment. Registration records the creator, source and
licence while leaving human review pending. A documented CC0 basis is evidence,
not a guarantee that no third party could raise a claim. Identifiable people,
artwork, trademarks or suspicious authorship require separate assessment.

The current `media_asset.representation` vocabulary uses `concept_illustration`
for non-product contextual visuals. These records additionally declare the more
specific `context_photograph` representation in metadata and plain-language
credits; they are not described as AI-generated or as the project's own photos.

`scripts/prepare_context_variant.py` replaces explicit image slots in a new recipe,
preserving the old recipe/video, factual cells, music and creative controls. It
binds replacement asset versions and resets their crop to the full supplied image.
Rendering still runs through the existing recipe-admission boundary. A variant
does not approve itself or bypass factual, source-policy or final-human-review
gates. The nature/context variant is not a new permanent creative preference.

Primary guidance: [Commons reuse](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia)
and the [CC0 dedication](https://creativecommons.org/publicdomain/zero/1.0/).
Execution outcomes belong in the checkpoint, not inferred from these documents.
