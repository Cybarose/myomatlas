"""FastAPI entry point for Myomatlas.

Routes: /health, /cases, /mesh/{case_id} serving the reconstructed GLB, and
POST /analyze which runs the real pipeline (U-Net segmentation, measurements, then
the Claude agent) and returns the structured report plus the patient explanation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import pipeline
from .agent.agent import analyze_case
from .agent.schemas import AnalyzeRequest
from .cv.umd_loader import list_cases

app = FastAPI(title="Myomatlas API", version="0.1.0")

# The frontend runs on a different dev port, so keep CORS open.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cases")
def cases() -> JSONResponse:
    try:
        return JSONResponse(content={"cases": list_cases()})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": f"Could not list cases: {exc}"})


@app.get("/mesh/{case_id}")
def mesh(case_id: str):
    """Serve the GLB reconstructed from the predicted mask for this case."""
    try:
        path = pipeline.mesh_path(case_id)
    except Exception as exc:
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
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "error": f"Could not measure {request.case_id}: {exc}",
                },
            )

    # Only the fields the clinician actually filled in reach the agent.
    intake = request.intake.model_dump(exclude_none=True) if request.intake else {}
    result = analyze_case(measurements, intake)
    # The frontend renders the numbers next to the reasoning, so ship both together.
    result["measurements"] = measurements
    return JSONResponse(status_code=200 if result.get("ok") else 502, content=result)
