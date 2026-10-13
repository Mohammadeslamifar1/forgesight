# Setup and operation

Use Python 3.14 and Node.js 24 for the tested dependency set. Install CPU PyTorch from the official index before installing dependencies under `requirements.lock`.

## Prepared PyCharm folder

If `.venv`, `data/datasets`, and `artifacts/active.json` exist, select the existing interpreter and run `run.py`. FastAPI serves the built frontend at http://127.0.0.1:8010.

Rebuild UI changes with `npm run build --prefix web`. Restart `run.py` after Python edits. For UI hot reload, `npm run dev --prefix web` forwards `/api` to port 8010.

## Fresh environment

Follow the README commands in order. `setup` runs download, fit, and evaluation. It needs outbound access to Hugging Face's pinned dataset mirror and `download.pytorch.org` for pretrained weights. Later inspections run offline.

The downloader checks each file against its pinned SHA-256 LFS hash or Git blob hash, records a SHA-256 manifest, and retries temporary failures. Re-running it verifies existing files. Fitting and evaluation reject checksum mismatches. Dataset terms: CC BY-NC-SA 4.0, non-commercial use.

## Windows troubleshooting

- **Torchvision blocked by App Control:** this project does not import Torchvision native operators. It defines the needed ResNet layers in PyTorch and loads the official weight mapping.
- **Compiled Black blocked:** reinstall the formatter from source with `python -m pip install --force-reinstall --no-binary=black -c requirements.lock black`. Do not disable Windows security settings.
- **Playwright browser blocked:** Windows defaults to installed Microsoft Edge. `FORGESIGHT_BROWSER_CHANNEL` can select another installed supported Chromium channel.
- **Port occupied:** stop the other server, or use `python -m forgesight.cli serve --port 8012`. The development proxy and browser-test server have separate configured ports.
- **No model loaded:** run `python -m forgesight.cli setup`, then restart the server.
- **Artifact integrity failure:** retain the affected bundle for investigation and generate a new one with `fit`; do not skip verification to load modified weights.

## GPU use

The documented installation uses CPU PyTorch, which is sufficient for the app and benchmark. The CLI accepts `--device cuda` for fitting, evaluation, and serving when a compatible CUDA-enabled PyTorch environment is installed. GPU execution is not part of recorded verification; CPU timings are not GPU claims.

## Paths and environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `FORGESIGHT_ROOT` | Editable source root | Frontend and tracked reports |
| `FORGESIGHT_DATA` | `ROOT/data` | Dataset and private inspection records |
| `FORGESIGHT_ARTIFACTS` | `ROOT/artifacts` | Model bundles and active pointer |
| `FORGESIGHT_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Accepted HTTP hosts |
| `FORGESIGHT_BROWSER_CHANNEL` | Edge on Windows; Chromium elsewhere | Playwright browser |

Use absolute paths for overrides. A wheel installation outside the source checkout should set `FORGESIGHT_ROOT`; Docker does this explicitly.

## Storage

Uploaded originals are decoded in memory. The app persists a 224 × 224 RGB source copy, heatmap, and overlay; it does not retain the full-resolution original or image metadata. JSON exports reference local image endpoints rather than embedding the images. To inspect a historical upload again, select its original file or another sample explicitly.

No automatic retention policy is implemented. Back up the SQLite database, `data/inspections/`, and corresponding model artifacts together. Reviews append through the API, but the local database is not a tamper-proof audit ledger.

Compose has its own persistent volumes and model setup. `docker compose down` stops containers without deleting data; adding `--volumes` deletes stored data and artifacts.
