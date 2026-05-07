"""Schemas Pydantic del API publico."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Decision(str, Enum):
    APROBADO = "Aprobado"
    NEGADO = "Negado"
    DOCUMENTOS_FALTANTES = "Documentos_Faltantes"


class AuthorizeRequest(BaseModel):
    id_informe: str = Field(..., description="ID del informe medico (ej. INF-001)")
    cedula: str = Field(..., description="Cedula del paciente segun la aseguradora")


class AuthorizeResponse(BaseModel):
    id_informe: str
    cedula: str
    decision: Decision
    justificacion: str
    clausula_aplicada: Optional[str] = None
    documentos_faltantes: list[str] = Field(default_factory=list)
    id_decision: str
    timestamp: datetime
