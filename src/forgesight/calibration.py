"""Normal-only split-conformal threshold; scores are distances, not probabilities."""

import math

import numpy as np


def calibrate(scores: list[float], alpha: float = 0.05) -> dict:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Calibration requires finite normal scores.")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between zero and one.")
    rank = math.ceil((len(values) + 1) * (1 - alpha))
    if rank > len(values):
        raise ValueError("Too few calibration examples for the requested false-alarm target.")
    return {
        "method": "normal-only split conformal",
        "alpha": alpha,
        "rank": rank,
        "count": len(values),
        "threshold": float(np.sort(values)[rank - 1]),
        "scores": values.tolist(),
        "comparison": "score > threshold",
    }


def tail_fraction(score: float, calibration_scores: list[float]) -> float:
    """Smoothed upper-tail rank, NOT a probability that a part is defective."""
    values = np.asarray(calibration_scores)
    return float((1 + np.count_nonzero(values >= score)) / (len(values) + 1))
