"""Explicit application paths; no dependency on the caller's working directory."""

import os
from pathlib import Path

ROOT = Path(os.environ.get("FORGESIGHT_ROOT", Path(__file__).resolve().parents[2])).resolve()
DATA = Path(os.environ.get("FORGESIGHT_DATA", ROOT / "data")).resolve()
ARTIFACTS = Path(os.environ.get("FORGESIGHT_ARTIFACTS", ROOT / "artifacts")).resolve()


def atomic_json(path: Path, value: dict):
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)
