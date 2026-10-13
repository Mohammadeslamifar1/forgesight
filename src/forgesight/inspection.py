"""Bounded image decoding, single-flight inference, and an append-only review log."""

import io
import json
import sqlite3
import threading
import time
import uuid
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps, UnidentifiedImageError

from .calibration import tail_fraction
from .data import test_samples
from .model import IMAGE_SIZE, Detector
from .registry import read_bundle

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 12_000_000


class InspectionBusy(Exception):
    pass


def decode_image(payload: bytes) -> Image.Image:
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Choose a PNG or JPEG image smaller than 8 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as image:
                if image.format not in {"PNG", "JPEG"}:
                    raise ValueError("Only PNG and JPEG images are supported.")
                if image.width * image.height > MAX_PIXELS or min(image.size) < 32:
                    raise ValueError(
                        "Images must be at least 32 px per side and at most 12 megapixels."
                    )
                image.load()
                return ImageOps.exif_transpose(image).convert("RGB")
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as error:
        raise ValueError("The image could not be safely decoded.") from error


def visualizations(image: Image.Image, heatmap: np.ndarray, threshold: float):
    """A fixed distance scale across images; no misleading per-image min/max normalization."""
    source = image.resize((IMAGE_SIZE, IMAGE_SIZE), Image.Resampling.BILINEAR)
    normalized = np.clip(heatmap / max(threshold * 1.5, 1e-6), 0, 1)
    stops = np.array([0, 0.35, 0.65, 0.85, 1])
    colors = np.array(
        [[15, 28, 53], [28, 121, 148], [111, 207, 166], [252, 209, 89], [239, 80, 53]]
    )
    heat = np.stack([np.interp(normalized, stops, colors[:, i]) for i in range(3)], axis=-1)
    alpha = (0.1 + 0.6 * normalized)[..., None]
    overlay = np.asarray(source) * (1 - alpha) + heat * alpha
    return source, Image.fromarray(heat.astype(np.uint8)), Image.fromarray(overlay.astype(np.uint8))


class InspectionService:
    def __init__(self, data: Path, artifacts: Path, device="cpu", detector=None, metadata=None):
        self.data, self.artifacts = data, artifacts
        self.data.mkdir(parents=True, exist_ok=True)
        self.database = data / "inspections.sqlite3"
        self.lock = threading.Lock()
        self.detector = detector
        self.metadata = metadata
        self.report = None
        self.error = None
        if detector is None:
            try:
                torch.set_num_threads(4)
                folder, self.metadata = read_bundle(artifacts)
                self.detector = Detector.load(folder / "weights.pt", device)
            except (FileNotFoundError, ValueError, RuntimeError) as error:
                self.error = str(error)
        if self.metadata:
            report_path = artifacts / "reports" / f"{self.metadata['model_id']}.json"
            if report_path.exists():
                self.report = json.loads(report_path.read_text(encoding="utf-8"))
        self.samples = {row["id"]: row for row in test_samples(data / "datasets", "bottle")}
        with self.connect() as database:
            database.executescript("""
                CREATE TABLE IF NOT EXISTS inspections (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, result TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY, inspection_id TEXT NOT NULL REFERENCES inspections(id),
                    created_at TEXT NOT NULL, label TEXT NOT NULL, note TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS reviews_inspection ON reviews(inspection_id);
                """)

    @contextmanager
    def connect(self):
        database = sqlite3.connect(self.database, timeout=5)
        database.row_factory = sqlite3.Row
        database.execute("PRAGMA journal_mode=WAL")
        database.execute("PRAGMA foreign_keys=ON")
        try:
            with database:
                yield database
        finally:
            database.close()

    def inspect(self, payload: bytes, name: str, sample_id: str | None = None) -> dict:
        if self.detector is None or not self.metadata:
            raise RuntimeError("No model loaded. Run python -m forgesight.cli setup first.")
        if not self.lock.acquire(blocking=False):
            raise InspectionBusy("Another inspection is running. Try again shortly.")
        try:
            image = decode_image(payload)
            started = time.perf_counter()
            score, heatmap = self.detector.predict(image)
            elapsed = (time.perf_counter() - started) * 1000
            if not np.isfinite(score) or not np.isfinite(heatmap).all():
                raise RuntimeError("The model returned non-finite values.")
            calibration = self.metadata["calibration"]
            threshold = calibration["threshold"]
            identifier = uuid.uuid4().hex
            folder = self.data / "inspections" / identifier
            folder.mkdir(parents=True)
            outputs = visualizations(image, heatmap, threshold)
            for kind, output in zip(("source", "heatmap", "overlay"), outputs):
                output.save(folder / f"{kind}.png")
            result = {
                "id": identifier,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "name": Path(name).name[:140],
                "sample_id": sample_id,
                "model_id": self.metadata["model_id"],
                "score": score,
                "threshold": threshold,
                "flagged": score > threshold,
                "normal_tail_rank": tail_fraction(score, calibration["scores"]),
                "inference_ms": round(elapsed, 2),
                "original_size": list(image.size),
                "images": {
                    kind: f"/api/inspections/{identifier}/images/{kind}"
                    for kind in ("source", "heatmap", "overlay")
                },
                "scope": "Bottle appearance only. Unrelated inputs can produce misleading results.",
            }
            with self.connect() as database:
                database.execute(
                    "INSERT INTO inspections VALUES (?, ?, ?)",
                    (identifier, result["created_at"], json.dumps(result, allow_nan=False)),
                )
            return {**result, "reviews": []}
        finally:
            self.lock.release()

    def get(self, identifier: str) -> dict:
        with self.connect() as database:
            row = database.execute(
                "SELECT result FROM inspections WHERE id=?", (identifier,)
            ).fetchone()
            if not row:
                raise KeyError(identifier)
            result = json.loads(row["result"])
            result["reviews"] = [
                dict(row)
                for row in database.execute(
                    "SELECT id, created_at, label, note FROM reviews "
                    "WHERE inspection_id=? ORDER BY created_at",
                    (identifier,),
                )
            ]
            return result

    def history(self, limit=30, offset=0) -> dict:
        with self.connect() as database:
            identifiers = database.execute(
                "SELECT id FROM inspections ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            count = database.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
        return {"items": [self.get(row["id"]) for row in identifiers], "total": count}

    def review(self, identifier: str, label: str, note: str) -> dict:
        self.get(identifier)
        with self.connect() as database:
            database.execute(
                "INSERT INTO reviews VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, identifier, datetime.now(timezone.utc).isoformat(), label, note),
            )
        return self.get(identifier)
