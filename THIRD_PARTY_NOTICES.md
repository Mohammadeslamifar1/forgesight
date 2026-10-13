# Third-party material

The project's original source code is MIT licensed. That license does not replace the terms of external datasets, model weights, fonts, or dependencies.

## MVTec AD

Paul Bergmann, Michael Fauser, David Sattlegger, Carsten Steger. *MVTec AD — A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection*, CVPR 2019.

- Official source: https://www.mvtec.com/research-teaching/datasets/mvtec-ad
- Dataset license: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.
- Download mirror: `foersben/mvtec-ad` on Hugging Face, revision `c75b39616f84db43677bcc8228caaafaf5096d7f`.
- Original dataset images and masks are downloaded locally and excluded from Git. The dataset's license/readme files are preserved locally.
- `docs/images/inspection.png` and `docs/images/mobile.png` contain MVTec bottle images; the inspection screenshot also contains an anomaly-map overlay. These two screenshots are adaptations distributed under **CC BY-NC-SA 4.0**, with attribution to MVTec Software GmbH / Bergmann et al. Original app interface elements are by this project. Do not interpret the source-code MIT license as commercial permission for the dataset imagery.

## ResNet and torchvision

Kaiming He et al. *Deep Residual Learning for Image Recognition*, CVPR 2016. https://arxiv.org/abs/1512.03385

The ResNet-18 feature implementation uses the architecture and parameter layout of torchvision's ResNet basic blocks, adapted to retain only layers required for feature extraction. Torchvision code is BSD-3-Clause licensed; its full notice is retained in [docs/TORCHVISION_LICENSE.txt](docs/TORCHVISION_LICENSE.txt).

The ImageNet-1K V1 weights are downloaded from `https://download.pytorch.org/models/resnet18-f37072fd.pth` using PyTorch's hash-checked loader, then embedded in a local model bundle. They are not committed to Git. Pretrained weights and ImageNet data have their own terms; consult [PyTorch's model documentation](https://docs.pytorch.org/vision/stable/models.html) before uses beyond this research project.

## PatchCore

Karsten Roth et al. *Towards Total Recall in Industrial Anomaly Detection*, CVPR 2022. https://arxiv.org/abs/2106.08265

ForgeSight's memory-bank approach is inspired by PatchCore. The code is an implementation for this project, with deliberately different backbone, candidate selection, bank size, image scoring, and calibration. It is not a reproduction of the paper's published benchmark scores.

## Interface assets

DM Sans is bundled through `@fontsource-variable/dm-sans` under the SIL Open Font License. Lucide icons are provided by `lucide-react` under ISC. Dependency packages retain their upstream license files. No external font request is needed to use the built app.
