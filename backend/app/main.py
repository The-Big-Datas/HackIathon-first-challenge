"""FastAPI app: Insurance Pre-Authorization Agent."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import authorization

app = FastAPI(
    title="Insurance Pre-Authorization Agent",
    version="0.1.0",
    description="Agente FastAPI + Claude para pre-autorizacion de cirugias.",
)

# Origins permitidos. Override con env var ALLOWED_ORIGINS (lista separada por
# comas) si la URL pública de Streamlit Community Cloud cambia.
_DEFAULT_ALLOWED_ORIGINS = ",".join(
    [
        "https://hackiathon-first-challenge-fgdkuc9ai2z8jqcacuyttz.streamlit.app",
        "http://localhost:8501",
    ]
)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", _DEFAULT_ALLOWED_ORIGINS).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(authorization.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
