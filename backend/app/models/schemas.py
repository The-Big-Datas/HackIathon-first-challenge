"""Schemas Pydantic del API publico."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

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


class InformeListItem(BaseModel):
    id_informe: str
    descripcion_procedimiento: str = ""
    hospital: str = ""


class InformeDetail(BaseModel):
    id_informe: str
    paciente_cedula: str = ""
    paciente_nombre: str = ""
    paciente_fecha_nacimiento: str = ""
    paciente_sexo: str = ""
    poliza_numero: str = ""
    plan_nombre: str = ""
    plan_nivel: str = ""
    plan_id: str = ""
    poliza_fecha_alta: str = ""
    poliza_estado: str = ""
    fecha_emision: str = ""
    hospital: str = ""
    medico_tratante: str = ""
    diagnostico_cie10: str = ""
    diagnostico_desc: str = ""
    procedimiento_cpt: str = ""
    descripcion_procedimiento: str = ""
    justificacion_clinica: str = ""
    fecha_programada: str = ""
    urgencia: str = ""
    documentos_adjuntos: list[str] = Field(default_factory=list)


class CoberturaResponse(BaseModel):
    cubierto: bool
    dias_carencia: int = 0
    documentos_requeridos: list[str] = Field(default_factory=list)


class TraceEntry(BaseModel):
    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: Any = None


class DecisionPayload(BaseModel):
    decision: str
    justificacion: str = ""
    clausula_aplicada: str = ""
    documentos_faltantes: list[str] = Field(default_factory=list)


class ProcesarResponse(BaseModel):
    trace: list[TraceEntry] = Field(default_factory=list)
    final_text: str = ""
    decision: Optional[DecisionPayload] = None
