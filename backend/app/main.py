"""FastAPI entry point for MyoMap.

Phase 0 keeps only the /health route. Further endpoints (CV measurements,
3D mesh, agent report) are added in later phases.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MyoMap API", version="0.1.0")

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
