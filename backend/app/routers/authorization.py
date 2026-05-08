"""Endpoints publicos consumidos por el frontend Streamlit."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AuthorizeRequest,
    AuthorizeResponse,
    CoberturaResponse,
    InformeDetail,
    InformeListItem,
    ProcesarResponse,
)
from app.services import notion_service
from app.services.agent_service import AgentError, run_authorization, run_procesar
from app.services.notion_service import NotFound

router = APIRouter(tags=["authorization"])


@router.post("/authorize", response_model=AuthorizeResponse)
def authorize(req: AuthorizeRequest) -> AuthorizeResponse:
    try:
        return run_authorization(req.id_informe, req.cedula)
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=f"Agente: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/informes", response_model=list[InformeListItem])
def list_informes() -> list[InformeListItem]:
    try:
        return [InformeListItem(**i) for i in notion_service.list_informes_summary()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/informes/{informe_id}", response_model=InformeDetail)
def get_informe(informe_id: str) -> InformeDetail:
    try:
        return InformeDetail(**notion_service.fetch_informe_full(informe_id))
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/coberturas/{codigo_cpt}/{plan_id}", response_model=CoberturaResponse
)
def get_cobertura(codigo_cpt: str, plan_id: str) -> CoberturaResponse:
    try:
        cob = notion_service.fetch_cobertura_by_plan_page(codigo_cpt, plan_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if cob is None:
        raise HTTPException(
            status_code=404,
            detail=f"sin regla para CPT {codigo_cpt} bajo plan {plan_id}",
        )
    return CoberturaResponse(**cob)


@router.post("/procesar/{informe_id}", response_model=ProcesarResponse)
def procesar(informe_id: str) -> ProcesarResponse:
    try:
        return ProcesarResponse(**run_procesar(informe_id))
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=f"Agente: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
