"""Local-first HTTP API. The default listener is loopback, with same-origin writes."""

import json
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .inspection import MAX_BYTES, InspectionBusy, InspectionService
from .paths import ARTIFACTS, DATA, ROOT


class SampleRequest(BaseModel):
    sample_id: str = Field(min_length=1, max_length=80)


class ReviewRequest(BaseModel):
    label: Literal["normal", "defect", "uncertain"]
    note: str = Field(min_length=5, max_length=1000)


def create_app(data: Path = DATA, artifacts: Path = ARTIFACTS, injected_service=None):
    @asynccontextmanager
    async def lifespan(application):
        application.state.service = injected_service or InspectionService(
            data, artifacts, os.environ.get("FORGESIGHT_DEVICE", "cpu")
        )
        yield

    application = FastAPI(title="ForgeSight inspection API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.environ.get(
            "FORGESIGHT_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
        ).split(","),
    )

    @application.middleware("http")
    async def guard(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and (
                urlsplit(origin).netloc != request.headers.get("host")
                or urlsplit(origin).scheme != request.url.scheme
            ):
                return JSONResponse(
                    {"detail": "Cross-origin writes are not allowed."}, status_code=403
                )
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    {"detail": "Cross-site writes are not allowed."}, status_code=403
                )
            try:
                length = int(request.headers.get("content-length", 0))
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)
            if length > MAX_BYTES:
                return JSONResponse({"detail": "Maximum request size is 8 MB."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'; font-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    def service() -> InspectionService:
        return application.state.service

    @application.get("/api/health")
    def health():
        return {
            "status": "ready" if service().detector else "setup_required",
            "model_id": (service().metadata or {}).get("model_id"),
        }

    @application.get("/api/model")
    def model():
        return {
            "metadata": service().metadata,
            "error": service().error,
            "runtime_device": str(getattr(service().detector, "device", "cpu")),
        }

    @application.get("/api/benchmark")
    def benchmark():
        if not service().report:
            raise HTTPException(404, "No benchmark report. Run the evaluate command.")
        return service().report

    @application.get("/api/samples")
    def samples():
        return [
            {**sample, "image": f"/api/samples/{sample['id']}/image"}
            for sample in service().samples.values()
        ]

    @application.get("/api/samples/{sample_id}/image")
    def sample_image(sample_id: str):
        sample = service().samples.get(sample_id)
        if not sample:
            raise HTTPException(404, "Sample not found.")
        return FileResponse(data / "datasets" / sample["path"], media_type="image/png")

    @application.post("/api/inspect/sample", status_code=201)
    def inspect_sample(body: SampleRequest):
        sample = service().samples.get(body.sample_id)
        if not sample:
            raise HTTPException(404, "Sample not found.")
        return perform(
            (data / "datasets" / sample["path"]).read_bytes(), body.sample_id, body.sample_id
        )

    def perform(payload: bytes, name: str, sample_id=None):
        try:
            return service().inspect(payload, name, sample_id)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except InspectionBusy as error:
            raise HTTPException(429, str(error), headers={"Retry-After": "1"}) from error
        except RuntimeError as error:
            raise HTTPException(503, str(error)) from error

    @application.post("/api/inspect/upload", status_code=201)
    async def inspect_upload(
        request: Request, name: str = Query(default="upload.png", max_length=140)
    ):
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_BYTES:
                raise HTTPException(413, "Maximum image size is 8 MB.")
            chunks.append(chunk)
        return await run_in_threadpool(perform, b"".join(chunks), name)

    @application.get("/api/inspections")
    def history(limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        return service().history(limit, offset)

    def get_inspection(identifier: str):
        if not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise HTTPException(404, "Inspection not found.")
        try:
            return service().get(identifier)
        except KeyError as error:
            raise HTTPException(404, "Inspection not found.") from error

    @application.get("/api/inspections/{identifier}")
    def inspection(identifier: str):
        return get_inspection(identifier)

    @application.get("/api/inspections/{identifier}/images/{kind}")
    def inspection_image(identifier: str, kind: Literal["source", "heatmap", "overlay"]):
        get_inspection(identifier)
        return FileResponse(
            data / "inspections" / identifier / f"{kind}.png", media_type="image/png"
        )

    @application.get("/api/inspections/{identifier}/export")
    def export(identifier: str):
        return Response(
            json.dumps(get_inspection(identifier), indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="forgesight-{identifier[:8]}.json"'
            },
        )

    @application.post("/api/inspections/{identifier}/reviews", status_code=201)
    def review(identifier: str, body: ReviewRequest):
        get_inspection(identifier)
        if len(body.note.strip()) < 5:
            raise HTTPException(422, "Add a meaningful review note.")
        return service().review(identifier, body.label, body.note.strip())

    frontend = ROOT / "web" / "dist"
    if frontend.exists():
        application.mount("/", StaticFiles(directory=frontend, html=True), name="web")
    return application


app = create_app()
