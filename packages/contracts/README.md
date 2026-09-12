# Contract package

Version `1.0` defines the first reusable BS CATS object workflow:

- `UniversalObject` preserves domain data, provenance, confidence, and metadata.
- `ObjectEvent` records append-only capture, curation, and review events.
- `HumanReview` prevents agent-curated objects from silently becoming active.
- `LocalObjectStore` provides a zero-cost development implementation before Firestore.

Run a local workflow from the repository root:

```bash
python3 scripts/object_cli.py capture \
  --type market_observation \
  --title "Example signal" \
  --purpose "Preserve a source-backed observation" \
  --source-url "https://example.com/source"

python3 scripts/object_cli.py list
python3 scripts/object_cli.py curate OBJECT_ID --confidence 0.75 --tag smart-glasses
python3 scripts/object_cli.py review OBJECT_ID --decision approved
python3 scripts/object_cli.py history OBJECT_ID
```

The default append-only store is `.local/object-events.jsonl`. It remains local and
is created with owner-only permissions. Use `BS_CATS_LOCAL_OBJECT_STORE` or
`--store` to select another path.

Future versions will add MCP payload, publish-job, and render-manifest contracts.
Keep schemas backward compatible where possible and version every contract.
