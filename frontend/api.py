"""Backend API client. Single integration boundary to the FastAPI service.

Every HTTP error normalizes to a BackendError so screens never see raw
requests exceptions or Python tracebacks.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional
from urllib.parse import quote

import requests

# Tighter GET timeout. Render free-tier cold-wake is ~30s per the project guide,
# so 20s guarantees a timeout on the first visit. 45s leaves headroom.
GET_TIMEOUT = 45.0
COBERTURA_TIMEOUT = 30.0
PROCESAR_TIMEOUT = 150.0

# Allowlisted decision values. The FastAPI agent emits exactly these three
# strings; anything else (casing drift, unexpected fourth state) gets normalized
# to "Unknown" so the verdict hero falls back to a neutral palette instead of
# silently rendering grey on a real decision.
DECISION_VALUES = ("Aprobado", "Negado", "Documentos_Faltantes")
DecisionValue = Literal["Aprobado", "Negado", "Documentos_Faltantes", "Unknown"]


def get_backend_url() -> str:
    """Read backend URL fresh — picks up env changes without reimport."""
    try:
        import streamlit as _st
        return _st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "http://localhost:8000"))
    except Exception:
        return os.getenv("BACKEND_URL", "http://localhost:8000")


ErrorKind = Literal["network", "timeout", "http", "decode"]

# Body-stripping for error_panel display. Strip 10-digit cedula-like sequences
# and other PII-shaped patterns before showing upstream error bodies in the
# debug expander.
_PII_PATTERNS = (
    re.compile(r"\b\d{10}\b"),
    re.compile(r"\bDEC-INF-\w+\b"),
    re.compile(r"\bPOL-\d+\b"),
)


def _scrub_pii(text: str) -> str:
    out = text
    for pat in _PII_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


@dataclass
class BackendError(Exception):
    kind: ErrorKind
    message: str
    url: str
    status: Optional[int] = None

    def __str__(self) -> str:
        return f"[{self.kind}] {self.message} ({self.url})"


def _normalize_decision(raw: str) -> str:
    """Map raw decision string to one of DECISION_VALUES + 'Unknown' fallback."""
    if not raw:
        return "Unknown"
    norm = raw.strip().replace(" ", "_")
    for v in DECISION_VALUES:
        if norm.lower() == v.lower():
            return v
    return "Unknown"


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


def _pick(d: dict[str, Any], flat_key: str, nested: dict[str, Any], nested_key: str, default: str = "") -> str:
    """Pick a value from a flat key first, falling back to a nested dict's key.

    Reduces the InformeDetail.from_dict isinstance ladder to one helper.
    """
    flat = d.get(flat_key)
    if flat:
        return flat
    if isinstance(nested, dict):
        return nested.get(nested_key, default) or default
    return default


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
            paciente_cedula=_pick(d, "paciente_cedula", paciente, "cedula"),
            paciente_nombre=_pick(d, "paciente_nombre", paciente, "nombre"),
            paciente_fecha_nacimiento=_pick(d, "paciente_fecha_nacimiento", paciente, "fecha_nacimiento"),
            paciente_sexo=_pick(d, "paciente_sexo", paciente, "sexo"),
            poliza_numero=_pick(d, "poliza_numero", poliza, "numero"),
            plan_nombre=_pick(d, "plan_nombre", plan, "nombre"),
            plan_nivel=_pick(d, "plan_nivel", plan, "nivel"),
            plan_id=_pick(d, "plan_id", plan, "id"),
            poliza_fecha_alta=_pick(d, "poliza_fecha_alta", poliza, "fecha_alta"),
            poliza_estado=_pick(d, "poliza_estado", poliza, "estado"),
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
        if not isinstance(d, dict):
            return cls(tool="", input={}, output=None)
        return cls(
            tool=d.get("tool", ""),
            input=d.get("input") or {},
            output=d.get("output"),
        )


@dataclass
class Decision:
    decision: str  # one of DECISION_VALUES or "Unknown"
    justificacion: str = ""
    clausula_aplicada: str = ""
    documentos_faltantes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Decision":
        return cls(
            decision=_normalize_decision(d.get("decision", "")),
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
        # Empty dict {} is meaningful — backend signaled "decision present but
        # not yet populated" — treat it as a Decision with all-empty fields,
        # not None. Only None/missing means "no decision at all".
        decision = (
            Decision.from_dict(decision_raw)
            if isinstance(decision_raw, dict)
            else None
        )
        return cls(
            trace=[
                TraceEntry.from_dict(t)
                for t in (d.get("trace") or [])
                if isinstance(t, dict)
            ],
            final_text=d.get("final_text", "") or "",
            decision=decision,
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
        # Truncate to 80 chars + scrub PII patterns before surfacing in error
        # panel (the message is rendered in the user-visible debug expander).
        scrubbed = _scrub_pii(resp.text[:80])
        raise BackendError(
            kind="http",
            status=resp.status_code,
            message=f"HTTP {resp.status_code}: {scrubbed}",
            url=url,
        )

    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise BackendError(kind="decode", message=f"Malformed JSON: {exc}", url=url) from exc


def fetch_informes() -> list[InformeListItem]:
    """GET /informes — returns the list of informes from the backend."""
    url = f"{get_backend_url().rstrip('/')}/informes"
    payload = _request_json("GET", url, timeout=GET_TIMEOUT)
    if not isinstance(payload, list):
        raise BackendError(
            kind="decode",
            message=f"Expected list, got {type(payload).__name__}",
            url=url,
        )
    return [InformeListItem.from_dict(item) for item in payload if isinstance(item, dict)]


@dataclass
class Cobertura:
    cubierto: bool = False
    dias_carencia: int = 0
    documentos_requeridos: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Cobertura":
        return cls(
            cubierto=bool(d.get("cubierto")),
            dias_carencia=int(d.get("dias_carencia") or 0),
            documentos_requeridos=list(d.get("documentos_requeridos") or []),
        )


def fetch_cobertura(cpt: str, plan_id: str) -> Optional[Cobertura]:
    """GET /coberturas/{cpt}/{plan_id} — returns the coverage rule.

    Returns None ONLY for 404 (no rule). Network/timeout/decode errors raise
    BackendError so callers can distinguish "no rule" from "backend down".
    """
    if not cpt or not plan_id:
        return None
    # URL-encode path segments — defensive against future callers passing
    # user-controlled values.
    url = f"{get_backend_url().rstrip('/')}/coberturas/{quote(cpt, safe='')}/{quote(plan_id, safe='')}"
    try:
        resp = requests.get(url, timeout=COBERTURA_TIMEOUT)
    except requests.exceptions.Timeout as exc:
        raise BackendError(kind="timeout", message=str(exc), url=url) from exc
    except requests.exceptions.ConnectionError as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc
    except requests.exceptions.RequestException as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc

    if resp.status_code == 404:
        # 404 body may carry the "no rule found" payload (cubierto=False).
        try:
            data = resp.json()
            if isinstance(data, dict) and "cubierto" in data:
                return Cobertura.from_dict(data)
        except (ValueError, AttributeError):
            pass
        return None
    if not resp.ok:
        scrubbed = _scrub_pii(resp.text[:80])
        raise BackendError(
            kind="http",
            status=resp.status_code,
            message=f"HTTP {resp.status_code}: {scrubbed}",
            url=url,
        )
    try:
        data = resp.json()
    except (ValueError, AttributeError) as exc:
        raise BackendError(kind="decode", message=f"Malformed JSON: {exc}", url=url) from exc
    if not isinstance(data, dict):
        raise BackendError(
            kind="decode",
            message=f"Expected object, got {type(data).__name__}",
            url=url,
        )
    return Cobertura.from_dict(data)


def fetch_informe_detail(informe_id: str) -> Optional[InformeDetail]:
    """GET /informes/{id} — returns the rich informe detail.

    Returns None when the endpoint is not implemented (404). All other errors
    raise BackendError so the screen can render a real error panel.
    """
    url = f"{get_backend_url().rstrip('/')}/informes/{quote(informe_id, safe='')}"
    try:
        resp = requests.get(url, timeout=GET_TIMEOUT)
    except requests.exceptions.Timeout as exc:
        raise BackendError(kind="timeout", message=str(exc), url=url) from exc
    except requests.exceptions.ConnectionError as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc
    except requests.exceptions.RequestException as exc:
        raise BackendError(kind="network", message=str(exc), url=url) from exc

    if resp.status_code == 404:
        return None
    if not resp.ok:
        scrubbed = _scrub_pii(resp.text[:80])
        raise BackendError(
            kind="http",
            status=resp.status_code,
            message=f"HTTP {resp.status_code}: {scrubbed}",
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
    url = f"{get_backend_url().rstrip('/')}/procesar/{quote(informe_id, safe='')}"
    payload = _request_json("POST", url, timeout=PROCESAR_TIMEOUT)
    if not isinstance(payload, dict):
        raise BackendError(
            kind="decode",
            message=f"Expected object, got {type(payload).__name__}",
            url=url,
        )
    return ProcesarResponse.from_dict(payload)
