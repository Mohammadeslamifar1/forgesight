"""Immutable model bundles with content checksums and an atomic active pointer."""

import json
import re
from pathlib import Path

from .data import digest
from .paths import atomic_json

MODEL_ID = re.compile(r"model-[a-zA-Z0-9-]{8,80}\Z")


def read_bundle(
    artifacts: Path, model_id: str | None = None, verify: bool = True
) -> tuple[Path, dict]:
    if model_id is None:
        pointer = artifacts / "active.json"
        if not pointer.exists():
            raise FileNotFoundError("No model is active. Run the setup command first.")
        model_id = json.loads(pointer.read_text(encoding="utf-8"))["model_id"]
    if not MODEL_ID.fullmatch(model_id):
        raise ValueError("Invalid model ID.")
    folder = artifacts / "models" / model_id
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if metadata["model_id"] != model_id:
        raise ValueError("Model identity mismatch.")
    if verify:
        for filename, checksum in metadata["files"].items():
            if filename not in {"weights.pt", "baseline.npy", "split.json"}:
                raise ValueError("Unexpected model artifact.")
            if digest(folder / filename) != checksum:
                raise ValueError(f"Model artifact checksum failed: {filename}")
    return folder, metadata


def activate(artifacts: Path, model_id: str):
    read_bundle(artifacts, model_id)
    atomic_json(artifacts / "active.json", {"model_id": model_id})
