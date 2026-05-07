"""FastAPI app: Insurance Pre-Authorization Agent."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import authorization

app = FastAPI(
    title="Insurance Pre-Authorization Agent",
    version="0.1.0",
    description="Agente FastAPI + Claude para pre-autorizacion de cirugias.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(authorization.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
