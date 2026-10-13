import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from forgesight.api import create_app
from forgesight.inspection import MAX_BYTES, InspectionService, decode_image


class DeterministicTestDetector:
    """A test double for HTTP/storage contracts, never used in the application."""

    def predict(self, image):
        score = float(np.asarray(image).mean() / 255 * 3)
        return score, np.full((224, 224), score, dtype=np.float32)


def encoded_image(color="white", size=(64, 64), format="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=format)
    return buffer.getvalue()


@pytest.fixture
def service(tmp_path):
    metadata = {"model_id": "model-test1234", "calibration": {"threshold": 2, "scores": [1] * 42}}
    return InspectionService(
        tmp_path / "data",
        tmp_path / "artifacts",
        detector=DeterministicTestDetector(),
        metadata=metadata,
    )


@pytest.fixture
def client(service):
    with TestClient(
        create_app(service.data, service.artifacts, injected_service=service)
    ) as client:
        yield client


def upload(client):
    response = client.post(
        "/api/inspect/upload?name=part.png",
        content=encoded_image(),
        headers={"Content-Type": "image/png"},
    )
    assert response.status_code == 201
    return response.json()


def test_inspect_review_export_and_persist(client, service):
    result = upload(client)
    assert result["flagged"]
    assert result["threshold"] == 2
    assert result["score"] == 3
    identifier = result["id"]
    assert client.get(result["images"]["overlay"]).headers["content-type"] == "image/png"
    for label in ("uncertain", "defect"):
        response = client.post(
            f"/api/inspections/{identifier}/reviews",
            json={"label": label, "note": f"Operator assessment: {label}"},
        )
        assert response.status_code == 201
    exported = client.get(f"/api/inspections/{identifier}/export")
    assert "attachment" in exported.headers["content-disposition"]
    assert [review["label"] for review in exported.json()["reviews"]] == ["uncertain", "defect"]
    assert exported.json()["score"] == 3
    assert service.get(identifier)["threshold"] == 2
    assert client.get("/api/inspections").json()["total"] == 1
    assert client.get("/api/inspections?offset=1").json()["items"] == []


def test_origin_and_hostname_protection(client):
    assert (
        client.post(
            "/api/inspect/upload",
            content=encoded_image(),
            headers={"Origin": "https://malicious.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/inspect/upload", content=encoded_image(), headers={"Sec-Fetch-Site": "cross-site"}
        ).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "untrusted.example"}).status_code == 400
    assert (
        client.post(
            "/api/inspect/upload", content=encoded_image(), headers={"Origin": "http://testserver"}
        ).status_code
        == 201
    )


def test_request_validation_and_limits(client):
    assert client.post("/api/inspect/upload", content=b"not an image").status_code == 422
    assert (
        client.post(
            "/api/inspect/upload", content=b"x", headers={"Content-Length": str(MAX_BYTES + 1)}
        ).status_code
        == 413
    )
    assert (
        client.post("/api/inspect/upload", content=encoded_image(size=(16, 16))).status_code == 422
    )
    assert (
        client.post("/api/inspect/upload", content=encoded_image(format="GIF")).status_code == 422
    )
    assert client.post("/api/inspect/sample", json={"sample_id": "../private"}).status_code == 404
    assert client.get("/api/inspections/secret").status_code == 404
    assert client.get("/api/inspections?limit=500").status_code == 422


def test_single_flight_rejects_simultaneous_inference(client, service):
    service.lock.acquire()
    try:
        response = client.post("/api/inspect/upload", content=encoded_image())
        assert response.status_code == 429
        assert response.headers["retry-after"] == "1"
    finally:
        service.lock.release()
    assert upload(client)["flagged"]


def test_invalid_review_never_writes(client):
    identifier = upload(client)["id"]
    for body in (
        {"label": "execute", "note": "This is invalid"},
        {"label": "normal", "note": "     "},
    ):
        assert client.post(f"/api/inspections/{identifier}/reviews", json=body).status_code == 422
    assert client.get(f"/api/inspections/{identifier}").json()["reviews"] == []


def test_image_pixel_limit_checked_before_decode():
    with pytest.raises(ValueError, match="megapixels"):
        decode_image(encoded_image(size=(4000, 3100)))


def test_missing_model_returns_setup_state(tmp_path):
    with TestClient(create_app(tmp_path / "data", tmp_path / "artifacts")) as client:
        assert client.get("/api/health").json()["status"] == "setup_required"
        assert client.post("/api/inspect/upload", content=encoded_image()).status_code == 503
        assert client.get("/api/benchmark").status_code == 404
