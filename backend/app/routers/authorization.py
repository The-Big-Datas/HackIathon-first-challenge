"""Endpoint POST /authorize."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import AuthorizeRequest, AuthorizeResponse
from app.services.agent_service import AgentError, run_authorization

router = APIRouter(tags=["authorization"])


@router.post("/authorize", response_model=AuthorizeResponse)
def authorize(req: AuthorizeRequest) -> AuthorizeResponse:
    try:
        return run_authorization(req.id_informe, req.cedula)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=f"Agente: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
