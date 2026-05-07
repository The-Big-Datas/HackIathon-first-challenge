from fastapi import FastAPI

from app.config import get_settings
from app.routers import authorization

settings = get_settings()

app = FastAPI(
    title="Insurance Pre-Authorization Agent",
    description="Agente IA que pre-autoriza cirugías cruzando informes médicos y pólizas en Notion.",
    version="1.0.0",
)

app.include_router(authorization.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level,
        reload=True,
    )
