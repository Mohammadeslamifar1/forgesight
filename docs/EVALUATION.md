# Evaluation protocol

This experiment uses only the MVTec AD **bottle** category. It is a category-specific research benchmark, not validation of a deployed production system.

## Fitting and data separation

The original training set contains 209 normal images. Sorted paths are shuffled using seed 17, yielding 167 fitting and 42 calibration images. The original 83 test images remain held out. The bundle stores split lists and image hashes; duplicate content crossing fit/calibration is rejected.

Only fitting images contribute to the memory bank and RGB baseline. The frozen encoder uses ImageNet-1K V1 weights; there is no gradient optimization on MVTec. Test labels and masks are used only for evaluation.

Input images become RGB at 224 × 224, with ImageNet channel normalization. ResNet-18 layer 2 and layer 3 maps receive 3 × 3 local averaging. Layer 3 is interpolated to layer 2's grid, then concatenated into 28 × 28 descriptors of dimension 384.

Up to 12,000 fitting patches are sampled. Farthest-first selection in a seeded 64-dimensional Gaussian projection chooses 512 representatives, retained in their full 384 dimensions. Inference computes Euclidean nearest-neighbor distances.

The image score averages the highest 1% of patch distances, rounded up (8 of 784 patches). Localization interpolates and smooths the distance grid with Gaussian sigma 4. Display scaling is fixed across inspections; heatmaps are not individually stretched to make each input appear suspicious.

## Calibration

For 42 normal scores and `alpha=0.05`:

```text
k = ceil((n + 1) × (1 - alpha)) = ceil(43 × 0.95) = 41
threshold = 41st smallest calibration score
flagged = image_score > threshold
```

The split-conformal false-alarm interpretation assumes exchangeable normal calibration and future normal data. Lighting, camera, viewpoint, or product shifts can break that assumption. Scores and upper-tail ranks are **not defect probabilities**.

The UI threshold slider recomputes test confusion counts without changing the saved model. Optimizing a threshold on these test labels leaks test information; such a choice needs a separate evaluation dataset.

## Metrics

- **Image AUROC:** ranking of defective versus normal images across thresholds.
- **Image average precision:** precision-recall summary, with defective images positive.
- **Pixel AUROC / average precision:** all test pixels pooled, with masks resized to 224 × 224 by nearest-neighbor interpolation. Background dominates pixel counts; average precision complements AUROC. These metrics do not establish precise defect boundaries.
- **Operating point:** TP, FP, TN, FN, precision, recall, F1, and normal-image false-alarm rate at the preselected threshold.
- **Baseline:** mean normal RGB template at 32 × 32; average of the top 11 squared per-pixel residuals. Same fitting and test split.
- **Latency:** three warm-ups followed by one timed prediction per test image; CPU, four threads. Includes preprocessing, inference and localization, excludes image I/O and HTTP.

The image AUROC interval uses 300 stratified percentile-bootstrap replicates, conditional on the fitted model. It excludes fitting/calibration uncertainty. Perfect ranking gives [1.0, 1.0] on this set: a limitation of this resampling result, **not evidence of zero generalization uncertainty**.

## Observed fixed-threshold behavior

| Condition | Image AUROC | Defects found | Normal false alarms |
| --- | ---: | ---: | ---: |
| Original | 1.000 | 63/63 | 1/20 |
| Brightness × 0.65 | 1.000 | 63/63 | 20/20 |
| Brightness × 1.35 | 1.000 | 63/63 | 3/20 |
| Gaussian blur radius 2 | 1.000 | 63/63 | 1/20 |

Stress probes reuse the same images with one transformation and hold the threshold fixed. They are diagnostic experiments, not independent datasets. Darkening illustrates score-distribution shift despite perfect ranking.

## Reproducibility limits

Revision pins, checksums, split manifests, configuration, and dependency locks make this experiment inspectable. OS, numerical libraries, processor, and threading can affect timing and slightly affect scores. Each fit has a new timestamp and artifact identity. Compare metrics/configuration rather than expecting every timestamp or serialized byte to match.

See [per-image predictions](../reports/bottle-baseline.json) and [research attribution](../THIRD_PARTY_NOTICES.md).
