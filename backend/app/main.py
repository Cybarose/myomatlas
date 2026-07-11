"""FastAPI-Einstieg fuer das AUB-Tool.

Haelt in Phase 0 nur die /health-Route. Weitere Endpunkte (CV-Messwerte,
3D-Mesh, Agent-Befund) kommen in spaeteren Phasen dazu.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AUB-Tool API", version="0.1.0")

# Frontend laeuft im Dev unter einem anderen Port, daher CORS offen halten.
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
