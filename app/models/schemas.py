from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class MedicalReport(BaseModel):
    """Informe médico digital recibido del Hospital."""

    report_id: str
    patient_id: str
    patient_name: str
    diagnosis: str
    procedure_code: str
    procedure_name: str
    requested_date: date
    attending_physician: str
    clinical_notes: str | None = None
    attachments: list[str] = Field(default_factory=list)


class InsurancePolicy(BaseModel):
    """Póliza del paciente registrada por la Aseguradora."""

    policy_id: str
    patient_id: str
    plan_name: str
    effective_date: date
    expiration_date: date
    covered_procedures: list[str] = Field(default_factory=list)
    excluded_procedures: list[str] = Field(default_factory=list)
    waiting_periods_months: dict[str, int] = Field(default_factory=dict)
    deductible: float = 0.0
    coverage_percentage: float = 100.0
    status: Literal["active", "suspended", "expired"] = "active"


Decision = Literal["pre_approved", "missing_documents", "rejected", "needs_review"]


class AuthorizationDecision(BaseModel):
    """Resultado del análisis emitido por el agente."""

    report_id: str
    patient_id: str
    decision: Decision
    rationale: str
    missing_documents: list[str] = Field(default_factory=list)
    coverage_percentage: float | None = None
    estimated_patient_cost: float | None = None
    issued_at: str


class AuthorizationRequest(BaseModel):
    """Body del endpoint para iniciar la pre-autorización."""

    report_id: str = Field(..., description="ID del informe médico en Notion")
    patient_id: str = Field(..., description="ID del paciente; usado para localizar la póliza")
