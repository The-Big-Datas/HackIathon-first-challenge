"""Backend API client. Single integration boundary to the FastAPI service.

Every HTTP error normalizes to a BackendError so screens never see raw
requests exceptions or Python tracebacks.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import requests


def get_backend_url() -> str:
    """Read backend URL fresh — picks up env changes without reimport."""
    try:
        import streamlit as _st
        return _st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "http://localhost:8000"))
    except Exception:
        return os.getenv("BACKEND_URL", "http://localhost:8000")


ErrorKind = Literal["network", "timeout", "http", "decode"]


@dataclass
class BackendError(Exception):
    kind: ErrorKind
    message: str
    url: str
    status: Optional[int] = None

    def __str__(self) -> str:
        return f"[{self.kind}] {self.message} ({self.url})"


@dataclass
class InformeListItem:
    id_informe: str
    descripcion_procedimiento: str
    hospital: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InformeListItem":
        return cls(
            id_informe=d.get("id_informe", ""),
            descripcion_procedimiento=d.get("descripcion_procedimiento", ""),
            hospital=d.get("hospital", ""),
        )


@dataclass
class InformeDetail:
    """Rich informe shape. Matches the guide's InformeMedico schema where it
    overlaps; extra fields the teammate may add (patient name, plan, fecha de
    alta) are accepted opportunistically. All fields default-empty so partial
    backend responses still render without raising.
    """

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
    documentos_adjuntos: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InformeDetail":
        # Accept either a flat shape or a nested {paciente: {...}, poliza: {...}} shape.
        paciente = d.get("paciente") or {}
        poliza = d.get("poliza") or {}
        plan = (poliza.get("plan") if isinstance(poliza, dict) else {}) or {}
        return cls(
            id_informe=d.get("id_informe", ""),
            paciente_cedula=d.get("paciente_cedula") or paciente.get("cedula", ""),
            paciente_nombre=d.get("paciente_nombre") or paciente.get("nombre", ""),
            paciente_fecha_nacimiento=d.get("paciente_fecha_nacimiento")
            or paciente.get("fecha_nacimiento", ""),
            paciente_sexo=d.get("paciente_sexo") or paciente.get("sexo", ""),
            poliza_numero=d.get("poliza_numero") or (poliza.get("numero", "") if isinstance(poliza, dict) else ""),
            plan_nombre=d.get("plan_nombre") or (plan.get("nombre", "") if isinstance(plan, dict) else ""),
            plan_nivel=d.get("plan_nivel") or (plan.get("nivel", "") if isinstance(plan, dict) else ""),
            plan_id=d.get("plan_id") or (plan.get("id", "") if isinstance(plan, dict) else ""),
            poliza_fecha_alta=d.get("poliza_fecha_alta")
            or (poliza.get("fecha_alta", "") if isinstance(poliza, dict) else ""),
            poliza_estado=d.get("poliza_estado")
            or (poliza.get("estado", "") if isinstance(poliza, dict) else ""),
            fecha_emision=d.get("fecha_emision", ""),
            hospital=d.get("hospital", ""),
            medico_tratante=d.get("medico_tratante", ""),
            diagnostico_cie10=d.get("diagnostico_cie10", ""),
            diagnostico_desc=d.get("diagnostico_desc", ""),
            procedimiento_cpt=d.get("procedimiento_cpt", ""),
            descripcion_procedimiento=d.get("descripcion_procedimiento", ""),
            justificacion_clinica=d.get("justificacion_clinica", ""),
            fecha_programada=d.get("fecha_programada", ""),
            urgencia=d.get("urgencia", ""),
            documentos_adjuntos=list(d.get("documentos_adjuntos") or []),
        )


@dataclass
class TraceEntry:
    tool: str
    input: dict[str, Any] = field(default_factory=dict)
    output: Any = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TraceEntry":
        return cls(
            tool=d.get("tool", ""),
            input=d.get("input") or {},
            output=d.get("output"),
        )


@dataclass
class Decision:
    decision: str
    justificacion: str = ""
    clausula_aplicada: str = ""
    documentos_faltantes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Decision":
        return cls(
            decision=d.get("decision", ""),
            justificacion=d.get("justificacion", ""),
            clausula_aplicada=d.get("clausula_aplicada", ""),
            documentos_faltantes=list(d.get("documentos_faltantes") or []),
        )


@dataclass
class ProcesarResponse:
    trace: list[TraceEntry] = field(default_factory=list)
    final_text: str = ""
    decision: Optional[Decision] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProcesarResponse":
        decision_raw = d.get("decision")
        return cls(
            trace=[TraceEntry.from_dict(t) for t in (d.get("trace") or [])],
            final_text=d.get("final_text", "") or "",
            decision=Decision.from_dict(decision_raw) if decision_raw else None,
        )


def _request_json(method: str, url: str, *, timeout: float) -> Any:
    try:
        resp = requests.request(method, url, timeout=timeout)
    except requests.exceptions.Timeout as exc:
        raise BackendError(kind="timeout", message=str(exc), url=url) from exc
    except requests.exceptions.ConnectionError as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc
    except requests.exceptions.RequestException as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc

    if not resp.ok:
        raise BackendError(
            kind="http",
            status=resp.status_code,
            message=f"HTTP {resp.status_code}: {resp.text[:200]}",
            url=url,
        )

    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise BackendError(kind="decode", message=f"Malformed JSON: {exc}", url=url) from exc


def fetch_informes() -> list[InformeListItem]:
    """GET /informes — returns the list of informes from the backend."""
    url = f"{get_backend_url().rstrip('/')}/informes"
    payload = _request_json("GET", url, timeout=20.0)
    if not isinstance(payload, list):
        raise BackendError(
            kind="decode",
            message=f"Expected list, got {type(payload).__name__}",
            url=url,
        )
    return [InformeListItem.from_dict(item) for item in payload]


@dataclass
class Cobertura:
    cubierto: bool = False
    dias_carencia: int = 0
    documentos_requeridos: list[str] = field(default_factory=list)
    motivo: str = ""

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cobertura":
        return cls(
            cubierto=bool(d.get("cubierto")),
            dias_carencia=int(d.get("dias_carencia") or 0),
            documentos_requeridos=list(d.get("documentos_requeridos") or []),
            motivo=d.get("motivo", "") or "",
        )


def fetch_cobertura(cpt: str, plan_id: str) -> Optional[Cobertura]:
    """GET /coberturas/{cpt}/{plan_id} — returns the coverage rule. None if 404."""
    if not cpt or not plan_id:
        return None
    url = f"{get_backend_url().rstrip('/')}/coberturas/{cpt}/{plan_id}"
    try:
        resp = requests.get(url, timeout=10.0)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code == 404:
        # 404 may carry the "no rule found" payload; treat as no coverage
        try:
            data = resp.json()
            if isinstance(data, dict) and "cubierto" in data:
                return Cobertura.from_dict(data)
        except (ValueError, AttributeError):
            pass
        return None
    if not resp.ok:
        return None
    try:
        data = resp.json()
    except (ValueError, AttributeError):
        return None
    return Cobertura.from_dict(data) if isinstance(data, dict) else None


def fetch_informe_detail(informe_id: str) -> Optional[InformeDetail]:
    """GET /informes/{id} — returns the rich informe detail.

    Returns None when the endpoint is not implemented (404). All other errors
    raise BackendError so the screen can render a real error panel.
    """
    url = f"{get_backend_url().rstrip('/')}/informes/{informe_id}"
    try:
        resp = requests.get(url, timeout=20.0)
    except requests.exceptions.Timeout as exc:
        raise BackendError(kind="timeout", message=str(exc), url=url) from exc
    except requests.exceptions.ConnectionError as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc
    except requests.exceptions.RequestException as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc

    if resp.status_code == 404:
        return None
    if not resp.ok:
        raise BackendError(
            kind="http",
            status=resp.status_code,
            message=f"HTTP {resp.status_code}: {resp.text[:200]}",
            url=url,
        )
    try:
        payload = resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise BackendError(kind="decode", message=f"Malformed JSON: {exc}", url=url) from exc
    if not isinstance(payload, dict):
        raise BackendError(
            kind="decode",
            message=f"Expected object, got {type(payload).__name__}",
            url=url,
        )
    return InformeDetail.from_dict(payload)


def procesar_informe(informe_id: str) -> ProcesarResponse:
    """POST /procesar/{informe_id} — runs the agent and returns the result."""
    url = f"{get_backend_url().rstrip('/')}/procesar/{informe_id}"
    payload = _request_json("POST", url, timeout=120.0)
    if not isinstance(payload, dict):
        raise BackendError(
            kind="decode",
            message=f"Expected object, got {type(payload).__name__}",
            url=url,
        )
    return ProcesarResponse.from_dict(payload)
