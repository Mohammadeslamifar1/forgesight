"""Compact PatchCore-inspired model with a frozen ResNet-18 feature encoder.

Deliberate differences from the paper: ResNet-18, candidate subsampling, a small
projected greedy coreset, and a top-1% distance image score without reweighting.
"""

import math
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageOps
from scipy.ndimage import gaussian_filter
from torch import nn

IMAGE_SIZE = 224


def preprocess(image: Image.Image) -> torch.Tensor:
    image = (
        ImageOps.exif_transpose(image)
        .convert("RGB")
        .resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    )
    array = np.asarray(image, dtype=np.float32).copy() / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1)
    mean = torch.tensor([0.485, 0.456, 0.406])[:, None, None]
    std = torch.tensor([0.229, 0.224, 0.225])[:, None, None]
    return (tensor - mean) / std


class ResidualBlock(nn.Module):
    """ResNet basic block; parameter names match the official torchvision weights."""

    def __init__(self, incoming: int, outgoing: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv2d(incoming, outgoing, 3, stride, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(outgoing)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(outgoing, outgoing, 3, 1, 1, bias=False)
        self.bn2 = nn.BatchNorm2d(outgoing)
        self.downsample = (
            nn.Sequential(
                nn.Conv2d(incoming, outgoing, 1, stride, bias=False), nn.BatchNorm2d(outgoing)
            )
            if stride != 1 or incoming != outgoing
            else None
        )

    def forward(self, inputs):
        identity = inputs if self.downsample is None else self.downsample(inputs)
        result = self.relu(self.bn1(self.conv1(inputs)))
        return self.relu(self.bn2(self.conv2(result)) + identity)


class Encoder(nn.Module):
    def __init__(self, pretrained: bool = False):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, 7, 2, 3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(3, 2, 1)
        self.layer1 = nn.Sequential(ResidualBlock(64, 64), ResidualBlock(64, 64))
        self.layer2 = nn.Sequential(ResidualBlock(64, 128, 2), ResidualBlock(128, 128))
        self.layer3 = nn.Sequential(ResidualBlock(128, 256, 2), ResidualBlock(256, 256))
        if pretrained:
            weights = torch.hub.load_state_dict_from_url(
                "https://download.pytorch.org/models/resnet18-f37072fd.pth",
                map_location="cpu",
                check_hash=True,
                weights_only=True,
            )
            self.load_state_dict(
                {
                    key: value
                    for key, value in weights.items()
                    if not key.startswith(("layer4.", "fc."))
                },
                strict=True,
            )
        self.requires_grad_(False)
        self.eval()

    def forward(self, images):
        stem = self.maxpool(self.relu(self.bn1(self.conv1(images))))
        first = self.layer2(self.layer1(stem))
        second = self.layer3(first)
        first = F.avg_pool2d(first, 3, stride=1, padding=1)
        second = F.avg_pool2d(second, 3, stride=1, padding=1)
        second = F.interpolate(second, size=first.shape[-2:], mode="bilinear", align_corners=False)
        return torch.cat([first, second], dim=1)


def greedy_coreset(features: torch.Tensor, size: int, seed: int = 17) -> torch.Tensor:
    """Greedy farthest-first sampling in a seeded 64-dimensional projection."""
    features = features.cpu().float()
    if not 1 <= size <= len(features):
        raise ValueError("Coreset size must be between 1 and the candidate count.")
    generator = torch.Generator().manual_seed(seed)
    projection = torch.randn(features.shape[1], 64, generator=generator) / math.sqrt(64)
    reduced = features @ projection
    selected = []
    minimum = torch.full((len(features),), float("inf"))
    index = int(torch.randint(len(features), (1,), generator=generator))
    for _ in range(size):
        selected.append(index)
        distance = ((reduced - reduced[index]) ** 2).sum(dim=1)
        minimum = torch.minimum(minimum, distance)
        minimum[selected] = -1
        index = int(torch.argmax(minimum))
    return features[selected].contiguous()


class Detector:
    def __init__(self, encoder: Encoder, bank: torch.Tensor, device: str = "cpu"):
        if bank.ndim != 2 or bank.shape[1] != 384 or not len(bank):
            raise ValueError("Invalid memory bank shape.")
        if not torch.isfinite(bank).all():
            raise ValueError("Non-finite memory bank.")
        self.device = torch.device(device)
        self.encoder = encoder.to(self.device).eval()
        self.bank = bank.to(self.device)

    @torch.inference_mode()
    def predict(self, image: Image.Image) -> tuple[float, np.ndarray]:
        features = self.encoder(preprocess(image).unsqueeze(0).to(self.device))
        _, _, height, width = features.shape
        patches = features.permute(0, 2, 3, 1).reshape(-1, 384)
        distances = torch.cdist(patches, self.bank).min(dim=1).values
        count = max(1, math.ceil(len(distances) * 0.01))
        score = float(distances.topk(count).values.mean().cpu())
        heatmap = (
            F.interpolate(
                distances.reshape(1, 1, height, width),
                size=(IMAGE_SIZE, IMAGE_SIZE),
                mode="bilinear",
                align_corners=False,
            )[0, 0]
            .cpu()
            .numpy()
        )
        return score, gaussian_filter(heatmap, sigma=4).astype(np.float32)

    def save(self, path: Path):
        torch.save(
            {
                "format_version": 1,
                "encoder": {key: value.cpu() for key, value in self.encoder.state_dict().items()},
                "bank": self.bank.cpu(),
            },
            path,
        )

    @classmethod
    def load(cls, path: Path, device: str = "cpu"):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        if checkpoint.get("format_version") != 1:
            raise ValueError("Unsupported model format.")
        encoder = Encoder()
        encoder.load_state_dict(checkpoint["encoder"], strict=True)
        return cls(encoder, checkpoint["bank"], device)
