from fastapi import APIRouter, HTTPException

from app.models.schemas import AuthorizationDecision, AuthorizationRequest
from app.services.agent_service import PreAuthorizationAgent

router = APIRouter(prefix="/authorize", tags=["authorization"])


@router.post("", response_model=AuthorizationDecision, status_code=200)
async def authorize(request: AuthorizationRequest) -> AuthorizationDecision:
    """Recibe un report_id + patient_id y devuelve una decisión instantánea."""
    agent = PreAuthorizationAgent()
    try:
        decision = await agent.run(request.report_id, request.patient_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent failure: {exc}") from exc
    return decision
