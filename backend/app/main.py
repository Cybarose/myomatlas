"""FastAPI entry point for Myomatlas.

Routes: /health, /cases, /mesh/{case_id} serving the reconstructed GLB, and
POST /analyze which runs the real pipeline (U-Net segmentation, measurements, then
the Claude agent) and returns the structured report plus the patient explanation.

Every route body is wrapped, and a catch-all handler sits behind them, so a single bad
case, a failed segmentation or a failed agent call answers the client with JSON and
leaves the server running.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import pipeline
from .agent.agent import analyze_case
from .agent.schemas import AnalyzeRequest
from .cv.umd_loader import list_cases

logger = logging.getLogger("myomatlas.api")

app = FastAPI(title="Myomatlas API", version="0.1.0")

# The frontend runs on a different dev port, so keep CORS open.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    """Last line of defence: log the traceback, answer the client, stay up."""
    logger.error("Unhandled error on %s\n%s", request.url.path, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": f"Internal error: {type(exc).__name__}: {exc}"},
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cases")
def cases() -> JSONResponse:
    try:
        return JSONResponse(content={"cases": list_cases()})
    except Exception as exc:
        logger.exception("Listing cases failed")
        return JSONResponse(status_code=500, content={"error": f"Could not list cases: {exc}"})


@app.get("/mesh/{case_id}")
def mesh(case_id: str):
    """Serve the GLB reconstructed from the predicted mask for this case."""
    try:
        path = pipeline.mesh_path(case_id)
    except Exception as exc:
        logger.exception("Mesh build failed for %s", case_id)
        return JSONResponse(
            status_code=404,
            content={"error": f"Could not build the mesh for {case_id}: {exc}"},
        )
    return FileResponse(path, media_type="model/gltf-binary", filename=f"{case_id}.glb")


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> JSONResponse:
    if not request.case_id and request.measurements is None:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Provide either case_id or measurements."},
        )

    measurements = request.measurements
    if measurements is None:
        try:
            measurements = pipeline.measurements(request.case_id)
        except Exception as exc:
            logger.exception("Measuring %s failed", request.case_id)
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": f"Could not measure {request.case_id}: {exc}"},
            )

    # analyze_case already turns model and network failures into an error dict, but a
    # crash anywhere in here must still not reach the server loop.
    try:
        intake = request.intake.model_dump(exclude_none=True) if request.intake else {}
        result = analyze_case(measurements, intake)
    except Exception as exc:
        logger.exception("Agent call failed for %s", request.case_id)
        return JSONResponse(
            status_code=502,
            content={"ok": False, "error": f"The analysis failed: {exc}"},
        )

    # The frontend renders the numbers next to the reasoning, so ship both together.
    result["measurements"] = measurements
    return JSONResponse(status_code=200 if result.get("ok") else 502, content=result)
