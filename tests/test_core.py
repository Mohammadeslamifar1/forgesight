import math

import numpy as np
import pytest
import torch
from PIL import Image

from forgesight.calibration import calibrate, tail_fraction
from forgesight.data import split_normal
from forgesight.evaluation import bootstrap_auc, operating_point, summarize
from forgesight.model import Detector, Encoder, greedy_coreset, preprocess
from forgesight.paths import atomic_json
from forgesight.registry import read_bundle

torch.set_num_threads(2)


def test_conformal_rank_and_strict_comparison():
    result = calibrate(list(range(42)))
    assert result["rank"] == math.ceil(43 * 0.95) == 41
    assert result["threshold"] == 40
    point = operating_point([0, 1], [40, 41], result["threshold"])
    assert point == {
        "tp": 1,
        "fp": 0,
        "tn": 1,
        "fn": 0,
        "precision": 1,
        "recall": 1,
        "false_positive_rate": 0,
        "f1": 1,
    }
    assert tail_fraction(100, list(range(42))) == 1 / 43
    assert tail_fraction(-1, list(range(42))) == 1


@pytest.mark.parametrize(
    "scores, alpha",
    [([], 0.05), ([float("nan")] * 42, 0.05), ([1, 2], 0.05), ([1] * 42, 0), ([1] * 42, 1)],
)
def test_invalid_calibration_rejected(scores, alpha):
    with pytest.raises(ValueError):
        calibrate(scores, alpha)


def test_split_is_reproducible_disjoint_and_excludes_test_data(tmp_path):
    folder = tmp_path / "bottle" / "train" / "good"
    folder.mkdir(parents=True)
    for index in range(100):
        (folder / f"{index:03}.png").write_bytes(str(index).encode())
    first = split_normal(tmp_path, "bottle")
    assert first == split_normal(tmp_path, "bottle")
    assert len(first["fit"]) == 80
    assert len(first["calibration"]) == 20
    assert set(first["fit"]).isdisjoint(first["calibration"])
    assert all("/train/good/" in name for name in first["fit"] + first["calibration"])
    assert first != split_normal(tmp_path, "bottle", seed=24)


def test_preprocess_has_expected_normalization():
    value = preprocess(Image.new("RGB", (300, 100), "white"))
    assert value.shape == (3, 224, 224)
    expected = torch.tensor([(1 - 0.485) / 0.229, (1 - 0.456) / 0.224, (1 - 0.406) / 0.225])
    assert torch.allclose(value[:, 50, 50], expected)


def test_coreset_keeps_extreme_modes_and_is_repeatable():
    features = torch.tensor([[0.0, 0.0], [0.01, 0.01], [50.0, 50.0], [50.01, 50.01]])
    selected = greedy_coreset(features, 2)
    assert torch.equal(selected, greedy_coreset(features, 2))
    assert selected.min() < 1 and selected.max() > 49
    with pytest.raises(ValueError):
        greedy_coreset(features, 0)


def test_model_serialization_preserves_predictions_without_network(tmp_path):
    torch.manual_seed(7)
    detector = Detector(Encoder(), torch.randn(8, 384))
    image = Image.new("RGB", (224, 224), (120, 90, 60))
    score, heatmap = detector.predict(image)
    detector.save(tmp_path / "model.pt")
    restored_score, restored_map = Detector.load(tmp_path / "model.pt").predict(image)
    assert score == pytest.approx(restored_score, abs=1e-6)
    np.testing.assert_allclose(heatmap, restored_map)
    assert heatmap.shape == (224, 224)
    assert np.isfinite(heatmap).all()


def test_registry_rejects_tampering_and_path_traversal(tmp_path):
    identifier = "model-12345678"
    folder = tmp_path / "models" / identifier
    folder.mkdir(parents=True)
    (folder / "weights.pt").write_bytes(b"changed")
    atomic_json(
        folder / "metadata.json", {"model_id": identifier, "files": {"weights.pt": "incorrect"}}
    )
    with pytest.raises(ValueError, match="checksum"):
        read_bundle(tmp_path, identifier)
    with pytest.raises(ValueError, match="Invalid model"):
        read_bundle(tmp_path, "../secret")


def test_metrics_distinguish_ranking_from_threshold_errors():
    labels, scores = [0, 0, 1, 1], [0.1, 0.2, 0.3, 0.4]
    result = summarize(labels, scores, 0.15)
    assert result["image_auroc"] == 1
    assert result["operating_point"]["fp"] == 1
    assert result["operating_point"]["precision"] == pytest.approx(2 / 3)
    assert bootstrap_auc(labels, scores, repetitions=20)["low"] == 1
    with pytest.raises(ValueError):
        summarize([1, 1], [0.1, 0.3], 0.2)


def test_no_positive_predictions_has_undefined_precision():
    assert operating_point([0, 1], [0.1, 0.2], 100)["precision"] is None
