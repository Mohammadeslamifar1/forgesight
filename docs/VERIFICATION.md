# Verification record

Final local application checks: **2026-10-13**, Windows, Python 3.14.2, Node.js 24.18.0, CPU PyTorch 2.11.0, installed Microsoft Edge through Playwright.

| Check | Observed result |
| --- | --- |
| Python suite | 21 tests passed |
| Statement coverage | 81.98% across 677 statements; not branch coverage |
| Real-model browser journeys | 7 tests passed |
| Production frontend | TypeScript and Vite build passed |
| Formatting/static checks | Black, isort, Flake8 and Prettier passed |
| Dataset integrity | All 357 downloaded files matched the pinned manifest |
| Model integrity | Weights, baseline and split manifest checksums verified |
| Mobile layout | No horizontal overflow at 390px on studio and performance pages |
| Automated accessibility | No axe WCAG 2 A/AA or 2.1 AA violations on the tested studio page |
| Container image | Multi-stage Linux Docker build passed with locked runtime dependencies |
| Container smoke test | Non-root UID 10001; real model load, defect prediction, review, export, overlay and UI passed |

Browser journeys cover real normal/defective predictions, heatmap view, human review, export, history, uploads, input validation, threshold exploration, model card, browser navigation, and mobile layout. The upload-history regression prevents accidentally rerunning an unrelated sample after reopening an uploaded image.

The Python lifecycle test performs tensor-based fit/save/load/evaluate using generated images and an untrained test encoder, with no external downloads. HTTP contract tests use a detector test double. The recorded MVTec benchmark and browser tests use the real ImageNet-pretrained model.

The numerical benchmark in `reports/bottle-baseline.json` was recorded on **2026-10-12**. Its timings are from that experiment, not the later concurrent test runs. See the report for full predictions and [evaluation methodology](EVALUATION.md) for interpretation.

The Linux container loaded the Windows-created model bundle and scored the first broken-large test image at 3.33484554 versus 3.33484578 in the recorded Windows run. This smoke test validates one cross-platform inference path; it is not a full Linux benchmark rerun.

The locked Starlette TestClient emits a dependency deprecation warning recommending `httpx2`; the test suite currently passes with locked `httpx`. No GPU benchmark, load test, comprehensive manual accessibility audit, formal security audit, or external hosted deployment is claimed.

The [GitHub Actions history](https://github.com/Mohammadeslamifar1/forgesight/actions) records hosted verification for published commits. This document records the local checks above; it does not substitute for a particular commit's CI result.
