"""Fit frozen deep features to normal images and calibrate on a disjoint split."""

import hashlib
import json
import platform
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .calibration import calibrate
from .data import DATASET_LICENSE, DATASET_REVISION, digest, split_normal, verify_provenance
from .model import IMAGE_SIZE, Detector, Encoder, greedy_coreset, preprocess
from .paths import atomic_json
from .registry import activate


def low_resolution(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB").resize((32, 32)), dtype=np.float32) / 255.0


def fit(
    data_root: Path,
    artifacts: Path,
    category: str = "bottle",
    seed: int = 17,
    bank_size: int = 512,
    device: str = "cpu",
) -> dict:
    started = time.perf_counter()
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    split = split_normal(data_root, category, seed)
    verify_provenance(data_root, category, split["fit"] + split["calibration"])
    hashes = {name: digest(data_root / name) for name in split["fit"] + split["calibration"]}
    fit_hashes = {hashes[name] for name in split["fit"]}
    if fit_hashes.intersection(hashes[name] for name in split["calibration"]):
        raise ValueError("Duplicate image content crosses fit/calibration boundary.")
    encoder = Encoder(pretrained=True).to(device)
    collected, templates = [], []
    with torch.inference_mode():
        for start in range(0, len(split["fit"]), 12):
            images = []
            for name in split["fit"][start : start + 12]:
                with Image.open(data_root / name) as image:
                    images.append(preprocess(image))
                    templates.append(low_resolution(image))
            features = encoder(torch.stack(images).to(device))
            collected.append(features.permute(0, 2, 3, 1).reshape(-1, 384).cpu())
            print(
                f"Encoded {min(start + 12, len(split['fit']))}/{len(split['fit'])} normal images",
                flush=True,
            )
    patches = torch.cat(collected)
    generator = torch.Generator().manual_seed(seed)
    candidates = patches[torch.randperm(len(patches), generator=generator)[:12000]]
    print(
        f"Selecting {bank_size} representative patches from {len(candidates)} candidates",
        flush=True,
    )
    bank = greedy_coreset(candidates, bank_size, seed)
    detector = Detector(encoder, bank, device)
    scores = []
    for name in split["calibration"]:
        with Image.open(data_root / name) as image:
            score, _ = detector.predict(image)
        scores.append(score)
    calibration = calibrate(scores)
    created = datetime.now(timezone.utc)
    staging = artifacts / f"staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=True)
    detector.save(staging / "weights.pt")
    np.save(staging / "baseline.npy", np.mean(templates, axis=0))
    split["sha256"] = hashes
    atomic_json(staging / "split.json", split)
    weight_digest = digest(staging / "weights.pt")
    model_id = f"model-{created.strftime('%Y%m%dT%H%M%S')}-{weight_digest[:8]}"
    metadata = {
        "model_id": model_id,
        "created_at": created.isoformat(),
        "method": "Deep patch memory",
        "paper_relationship": "PatchCore-inspired; not a faithful reproduction",
        "backbone": "ResNet-18 · ImageNet-1K V1 · frozen layers 2 + 3",
        "category": category,
        "input_size": IMAGE_SIZE,
        "bank_size": bank_size,
        "feature_dimension": 384,
        "candidate_count": len(candidates),
        "seed": seed,
        "fit_count": len(split["fit"]),
        "calibration": calibration,
        "score_definition": "Mean of highest 1% nearest-patch Euclidean distances",
        "dataset_revision": DATASET_REVISION,
        "data_license": DATASET_LICENSE,
        "split_sha256": hashlib.sha256(json.dumps(split, sort_keys=True).encode()).hexdigest(),
        "fit_seconds": round(time.perf_counter() - started, 3),
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": device,
        },
        "files": {
            name: digest(staging / name) for name in ("weights.pt", "baseline.npy", "split.json")
        },
    }
    atomic_json(staging / "metadata.json", metadata)
    destination = artifacts / "models" / model_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging.rename(destination)
    activate(artifacts, model_id)
    print(f"Active model: {model_id}; threshold {calibration['threshold']:.4f}", flush=True)
    return metadata
