"""Pinned, checksum-verified MVTec AD subset acquisition and split manifests."""

import hashlib
import json
import random
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .paths import atomic_json

DATASET_REPO = "foersben/mvtec-ad"
DATASET_REVISION = "c75b39616f84db43677bcc8228caaafaf5096d7f"
DATASET_LICENSE = "CC-BY-NC-SA-4.0"
CATEGORIES = ("bottle",)


def digest(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def download_dataset(root: Path, category: str = "bottle") -> dict:
    """Download one public mirror subset, with SHA-256 or Git blob integrity checks."""
    if category not in CATEGORIES:
        raise ValueError("This release supports the bottle category.")
    url = (
        f"https://huggingface.co/api/datasets/{DATASET_REPO}/tree/"
        f"{DATASET_REVISION}/{category}?recursive=true&limit=1000"
    )
    with urllib.request.urlopen(url, timeout=45) as response:
        files = [entry for entry in json.load(response) if entry["type"] == "file"]
        if response.headers.get("Link"):
            raise RuntimeError("Unexpected paginated manifest; refusing a partial dataset.")
    if not files:
        raise RuntimeError("Empty dataset manifest.")
    print(f"Dataset license: {DATASET_LICENSE}. Research/non-commercial use only.", flush=True)
    print(f"Downloading/verifying {len(files)} files from a pinned public mirror.", flush=True)

    def acquire(entry):
        relative = Path(entry["path"])
        destination = (root / relative).resolve()
        if not destination.is_relative_to(root.resolve()) or relative.parts[0] != category:
            raise ValueError("Unsafe dataset path.")

        def valid(payload: bytes):
            if len(payload) != entry["size"]:
                return False
            if entry.get("lfs"):
                return hashlib.sha256(payload).hexdigest() == entry["lfs"]["oid"]
            prefix = f"blob {len(payload)}\0".encode()
            return hashlib.sha1(prefix + payload).hexdigest() == entry["oid"]

        payload = destination.read_bytes() if destination.exists() else b""
        if not valid(payload):
            source = (
                f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/"
                f"{DATASET_REVISION}/{relative.as_posix()}"
            )
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(source, timeout=60) as response:
                        payload = response.read()
                    if not valid(payload):
                        raise ValueError(f"Checksum mismatch: {relative}")
                    break
                except (OSError, ValueError):
                    if attempt == 3:
                        raise
                    time.sleep(2**attempt)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".part")
            temporary.write_bytes(payload)
            temporary.replace(destination)
        return relative.as_posix(), hashlib.sha256(payload).hexdigest()

    checksums = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for index, (name, checksum) in enumerate(pool.map(acquire, files), 1):
            checksums[name] = checksum
            if index % 50 == 0:
                print(f"Verified {index}/{len(files)} files", flush=True)
    manifest = {
        "repository": DATASET_REPO,
        "revision": DATASET_REVISION,
        "license": DATASET_LICENSE,
        "category": category,
        "sha256": checksums,
    }
    atomic_json(root / f"{category}-provenance.json", manifest)
    return manifest


def split_normal(root: Path, category: str, seed: int = 17) -> dict:
    files = sorted((root / category / "train" / "good").glob("*.png"))
    if len(files) < 40:
        raise ValueError("At least 40 normal training images are required.")
    random.Random(seed).shuffle(files)
    calibration_count = max(20, round(len(files) * 0.2))
    calibration, fit = files[:calibration_count], files[calibration_count:]
    return {
        "seed": seed,
        "fit": sorted(p.relative_to(root).as_posix() for p in fit),
        "calibration": sorted(p.relative_to(root).as_posix() for p in calibration),
    }


def verify_provenance(root: Path, category: str, names: list[str]) -> dict:
    """Catch missing or edited dataset inputs before recording benchmark claims."""
    manifest = json.loads((root / f"{category}-provenance.json").read_text(encoding="utf-8"))
    if manifest["revision"] != DATASET_REVISION or manifest["repository"] != DATASET_REPO:
        raise ValueError("Dataset provenance differs from the pinned benchmark source.")
    for name in names:
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Unsafe dataset path.")
        if manifest["sha256"].get(name) != digest(path):
            raise ValueError(
                f"Dataset checksum failed: {name}. Download again before benchmarking."
            )
    return manifest


def test_samples(root: Path, category: str) -> list[dict]:
    samples = []
    for path in sorted((root / category / "test").glob("*/*.png")):
        defect = path.parent.name
        mask = root / category / "ground_truth" / defect / f"{path.stem}_mask.png"
        samples.append(
            {
                "id": f"{defect}-{path.stem}",
                "path": path.relative_to(root).as_posix(),
                "defect": defect,
                "anomalous": defect != "good",
                "mask": mask.relative_to(root).as_posix() if mask.exists() else None,
            }
        )
    return samples
