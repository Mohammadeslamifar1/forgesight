"""Fixed test-set evaluation, non-learned baseline, bootstrap intervals and shift probes."""

import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageEnhance, ImageFilter
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve

from .data import test_samples, verify_provenance
from .model import IMAGE_SIZE, Detector
from .paths import atomic_json
from .registry import read_bundle
from .training import low_resolution


def operating_point(labels, scores, threshold: float) -> dict:
    truth, predicted = np.asarray(labels, dtype=bool), np.asarray(scores) > threshold
    tp = int(np.sum(truth & predicted))
    fp = int(np.sum(~truth & predicted))
    tn = int(np.sum(~truth & ~predicted))
    fn = int(np.sum(truth & ~predicted))
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "false_positive_rate": fp / (fp + tn) if fp + tn else None,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
    }


def summarize(labels, scores, threshold: float) -> dict:
    labels, scores = np.asarray(labels), np.asarray(scores)
    if len(np.unique(labels)) != 2:
        raise ValueError("Evaluation requires normal and defective examples.")
    return {
        "image_auroc": float(roc_auc_score(labels, scores)),
        "image_average_precision": float(average_precision_score(labels, scores)),
        "operating_point": operating_point(labels, scores, threshold),
    }


def bootstrap_auc(labels, scores, seed=17, repetitions=300):
    labels, scores = np.asarray(labels), np.asarray(scores)
    generator = np.random.default_rng(seed)
    groups = [np.where(labels == value)[0] for value in (0, 1)]
    aucs = []
    for _ in range(repetitions):
        indexes = np.concatenate(
            [generator.choice(group, len(group), replace=True) for group in groups]
        )
        aucs.append(roc_auc_score(labels[indexes], scores[indexes]))
    return {
        "low": float(np.quantile(aucs, 0.025)),
        "high": float(np.quantile(aucs, 0.975)),
        "repetitions": repetitions,
        "method": "stratified percentile bootstrap; fixed fitted model and threshold",
    }


def evaluate(data_root: Path, artifacts: Path, device="cpu", shifts=True) -> dict:
    torch.set_num_threads(4)
    folder, metadata = read_bundle(artifacts)
    detector = Detector.load(folder / "weights.pt", device)
    baseline = np.load(folder / "baseline.npy", allow_pickle=False)
    samples = test_samples(data_root, metadata["category"])
    if not samples:
        raise ValueError("No test images found.")
    verify_provenance(
        data_root,
        metadata["category"],
        [row["path"] for row in samples] + [row["mask"] for row in samples if row["mask"]],
    )
    threshold = metadata["calibration"]["threshold"]
    pixel_labels, pixel_scores, latency, rows = [], [], [], []
    shift_scores = {"darker_0.65": [], "brighter_1.35": [], "blur_radius_2": []} if shifts else {}
    with Image.open(data_root / samples[0]["path"]) as image:
        for _ in range(3):
            detector.predict(image)
    for index, sample in enumerate(samples):
        with Image.open(data_root / sample["path"]) as image:
            image = image.convert("RGB")
            started = time.perf_counter()
            score, heatmap = detector.predict(image)
            latency.append((time.perf_counter() - started) * 1000)
            residual = np.square(low_resolution(image) - baseline).mean(axis=-1)
            baseline_score = float(np.mean(np.sort(residual.flatten())[-11:]))
            if shifts:
                variants = {
                    "darker_0.65": ImageEnhance.Brightness(image).enhance(0.65),
                    "brighter_1.35": ImageEnhance.Brightness(image).enhance(1.35),
                    "blur_radius_2": image.filter(ImageFilter.GaussianBlur(2)),
                }
                for key, variant in variants.items():
                    shift_scores[key].append(detector.predict(variant)[0])
        if sample["mask"]:
            with Image.open(data_root / sample["mask"]) as mask:
                truth = (
                    np.asarray(mask.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.NEAREST)) > 0
                )
        else:
            truth = np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=bool)
        pixel_labels.append(truth.flatten())
        pixel_scores.append(heatmap.flatten())
        rows.append(
            {
                **sample,
                "score": score,
                "baseline_score": baseline_score,
                "flagged": score > threshold,
            }
        )
        if (index + 1) % 20 == 0:
            print(f"Evaluated {index + 1}/{len(samples)} test images", flush=True)
    labels = [int(row["anomalous"]) for row in rows]
    scores = [row["score"] for row in rows]
    fpr, tpr, _ = roc_curve(labels, scores)
    baseline_scores = [row["baseline_score"] for row in rows]
    all_pixels, all_heatmaps = np.concatenate(pixel_labels), np.concatenate(pixel_scores)
    report = {
        "model_id": metadata["model_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "category": metadata["category"],
        "test_count": len(rows),
        "normal_count": labels.count(0),
        "defect_count": labels.count(1),
        "threshold": threshold,
        **summarize(labels, scores, threshold),
        "image_auroc_ci95": bootstrap_auc(labels, scores),
        "pixel_auroc": float(roc_auc_score(all_pixels, all_heatmaps)),
        "pixel_average_precision": float(average_precision_score(all_pixels, all_heatmaps)),
        "pixel_resolution": [IMAGE_SIZE, IMAGE_SIZE],
        "baseline": {
            "method": "Mean normal RGB template, top-1% squared pixel residual at 32 x 32",
            "image_auroc": float(roc_auc_score(labels, baseline_scores)),
            "image_average_precision": float(average_precision_score(labels, baseline_scores)),
        },
        "latency_ms": {
            "median": float(np.median(latency)),
            "p95": float(np.percentile(latency, 95)),
            "scope": "preprocess + encoder + nearest-neighbor + heatmap; "
            "excludes image I/O and HTTP",
            "device": device,
            "threads": 4,
            "warmup": 3,
        },
        "roc_curve": [{"fpr": float(x), "tpr": float(y)} for x, y in zip(fpr, tpr)],
        "shifts": {
            key: summarize(labels, values, threshold) for key, values in shift_scores.items()
        },
        "samples": rows,
        "limitations": [
            f"One category; {len(rows)} test images. "
            "No claim of performance on arbitrary products.",
            "Calibration assumes exchangeable normal images; "
            "camera and lighting shifts can break it.",
            "Scores and heatmap intensities are distances, not calibrated defect probabilities.",
            "Bootstrap intervals condition on a fixed model; "
            "they exclude fitting/calibration uncertainty.",
        ],
    }
    atomic_json(artifacts / "reports" / f"{metadata['model_id']}.json", report)
    print(
        f"Image AUROC: {report['image_auroc']:.4f}; pixel AUROC: {report['pixel_auroc']:.4f}",
        flush=True,
    )
    return report
