"""Exercise real tensor fitting/evaluation on fixtures, without downloading pretrained weights."""

import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from forgesight.data import DATASET_REPO, DATASET_REVISION, digest, verify_provenance
from forgesight.evaluation import evaluate
from forgesight.model import Encoder
from forgesight.paths import atomic_json
from forgesight.registry import read_bundle
from forgesight.training import fit


def fixture_dataset(root):
    for index in range(40):
        folder = root / "bottle" / "train" / "good"
        folder.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (64, 64), (70 + index, 85, 100))
        ImageDraw.Draw(image).ellipse((15, 15, 49, 49), fill=(160, 150, 140 + index))
        image.save(folder / f"{index:03}.png")
    for defect in ("good", "broken"):
        folder = root / "bottle" / "test" / defect
        folder.mkdir(parents=True)
        for index in range(2):
            image = Image.new("RGB", (64, 64), (88 + index, 85, 100))
            ImageDraw.Draw(image).ellipse((15, 15, 49, 49), fill=(160, 150, 155))
            if defect == "broken":
                ImageDraw.Draw(image).rectangle((20, 15, 45, 25), fill=(255, 0, 0))
                mask = Image.new("L", (64, 64))
                ImageDraw.Draw(mask).rectangle((20, 15, 45, 25), fill=255)
                target = root / "bottle" / "ground_truth" / defect
                target.mkdir(parents=True, exist_ok=True)
                mask.save(target / f"{index:03}_mask.png")
            image.save(folder / f"{index:03}.png")
    manifest = {
        "repository": DATASET_REPO,
        "revision": DATASET_REVISION,
        "sha256": {path.relative_to(root).as_posix(): digest(path) for path in root.rglob("*.png")},
    }
    atomic_json(root / "bottle-provenance.json", manifest)


def test_fit_reload_evaluate_and_tamper_detection(tmp_path, monkeypatch):
    dataset, artifacts = tmp_path / "dataset", tmp_path / "artifacts"
    fixture_dataset(dataset)
    monkeypatch.setattr("forgesight.training.Encoder", lambda pretrained: Encoder(pretrained=False))
    metadata = fit(dataset, artifacts, bank_size=8)
    assert metadata["fit_count"] == 20
    assert metadata["calibration"]["count"] == 20
    folder, restored = read_bundle(artifacts)
    assert restored == metadata
    split = json.loads((folder / "split.json").read_text())
    assert set(split["fit"]).isdisjoint(split["calibration"])
    report = evaluate(dataset, artifacts, shifts=True)
    assert report["test_count"] == 4
    assert len(report["shifts"]) == 3
    assert report["model_id"] == metadata["model_id"]
    assert report["threshold"] == metadata["calibration"]["threshold"]
    assert np.isfinite(report["pixel_average_precision"])
    image_path = dataset / "bottle" / "test" / "good" / "000.png"
    image_path.write_bytes(b"modified")
    with pytest.raises(ValueError, match="checksum"):
        verify_provenance(dataset, "bottle", [image_path.relative_to(dataset).as_posix()])
