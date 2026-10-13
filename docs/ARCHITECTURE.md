# Architecture and operating limits

## Model lifecycle

`download` acquires a pinned dataset subset and validates each file. `fit` separates normal fitting/calibration inputs, freezes a ResNet encoder, selects representative patches, and calibrates an alert threshold. Each fit produces a new model folder, not an overwrite of an older bundle. An atomic `active.json` pointer selects the next model to load.

Bundles contain tensor-only weights, the RGB baseline, split/hash manifest, and model metadata. The server verifies artifact checksums and loads with `weights_only=True`. This detects accidental changes; a local user able to alter weights and metadata can alter both. The format is not cryptographically signed provenance.

The server loads one model at startup. Changing the active pointer requires a restart. Inspections retain the model ID and original threshold, so later model changes do not rewrite historical findings.

## Inference and review

1. Accept a catalogued sample ID or raw PNG/JPEG bytes.
2. Enforce byte/pixel bounds and decode with Pillow, including EXIF orientation.
3. Normalize the input and compute nearest-memory-patch distances.
4. Store a resized source, heatmap, overlay, and immutable-through-API finding.
5. Append human reviews with timestamps and rationale.

Uploads are at most 8 MB and 12 megapixels, with each side at least 32 pixels. Inference uses a nonblocking process-local lock; concurrent requests receive 429 rather than silently queueing. There is no distributed worker queue.

SQLite WAL mode stores records and review events. Connections are short-lived, writes use transactions, and history is paginated. Images live in per-inspection directories. Database and filesystem writes are not one atomic transaction: an unexpected process failure can leave orphaned image directories. There is no background cleanup or retention policy.

The UI comparison slider reveals the original beside its overlay. Its benchmark threshold slider recomputes confusion counts locally and cannot change the active model. Human labels never trigger automatic retraining.

## Local security boundary

The default listener and Compose port binding are loopback-only. Host validation, same-origin write checks, bounded image parsing, CSP, and path-safe server-generated IDs reduce local browser attack exposure. There is no user authentication, workspace isolation, TLS termination, authorization role system, or audit signing.

Do not expose this service directly to a network. A shared deployment would need authentication/authorization, TLS, stronger global body/rate limits, retention controls, protected artifact storage, and a service-level concurrency design. No physical robot or production equipment is connected.

## Test boundaries

Core CI uses generated inputs to exercise calibration math, data split behavior, serialization, model fitting/evaluation, input limits, artifact tampering, concurrency, storage, reviews, and origin checks. An untrained encoder is used only in the synthetic lifecycle test to avoid network dependencies; HTTP tests use an explicit test double.

Browser tests use real fitted weights and the real dataset, an isolated temporary database, and real API calls. A separate manual benchmark workflow performs the complete data/model setup before running them. Fixed metrics in the repository are experimental records, not hardcoded inference output.

## Tradeoffs

| Choice | Benefit | Limit |
| --- | --- | --- |
| Frozen ResNet-18 | Small, CPU-friendly, established pretrained features | No domain-specific gradient adaptation |
| Compact patch memory | Inspectable normal reference, simple distance scoring | Appearance and alignment sensitivity |
| Separate normal calibration | No defect labels needed to choose threshold | Requires exchangeability; vulnerable to shifts |
| SQLite and local files | Simple offline operation | Single-user scope and no distributed transactions |
| Human review | Decisions remain explicit | No production quality-control automation |
| One category | Reproducible focused experiment | No cross-category or deployment generalization claim |
