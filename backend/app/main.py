"""FastAPI entry point for Myomatlas.

Routes: /health, and POST /analyze which runs the reasoning agent on a case id
or supplied measurements plus a clinical intake, returning the structured report.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .agent.agent import analyze_case, measurements_for_case
from .agent.schemas import AnalyzeRequest

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
            measurements = measurements_for_case(request.case_id)
        except Exception as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "error": f"Could not compute measurements for {request.case_id}: {exc}",
                },
            )

    intake = request.intake.model_dump() if request.intake else {}
    result = analyze_case(measurements, intake)
    return JSONResponse(status_code=200 if result.get("ok") else 502, content=result)
