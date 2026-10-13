# Changelog

## 0.1.0 — 2026-10-13

Initial research release.

- Frozen ResNet-18 feature extraction, normal patch-memory fitting, and separate threshold calibration.
- Reproducible MVTec AD bottle evaluation with an RGB baseline, pixel metrics, bootstrap intervals, and controlled image shifts.
- Inspection studio with uploads, heatmaps, comparison, human review, history, and JSON exports.
- Checksummed artifacts, pinned data revision, bounded inputs, and concurrency handling.
- Python tests, real-model browser tests, Docker packaging, documentation, and GitHub workflows.
- PyTorch 2.13.0 pin addresses GHSA-rrmf-rvhw-rf47 before the initial release.

Scope: local single-user research prototype, validated on one dataset category. Dataset images retain their non-commercial license; no production, multi-category, GPU, or robot-control validation is claimed.
