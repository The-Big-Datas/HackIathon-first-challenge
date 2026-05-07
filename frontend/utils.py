"""Pure helpers used across screens: dates, edad, doc labels, decision tone."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional


# Friendly Spanish labels for the document codes used in informes / coberturas.
DOC_LABEL: dict[str, str] = {
    "informe_quirurgico": "Informe quirúrgico",
    "examenes_prequirurgicos": "Exámenes prequirúrgicos",
    "segundo_dictamen": "Segundo dictamen médico",
    "exames_imagen": "Exámenes de imagen",
    "consentimiento": "Consentimiento informado",
}


# The 6 tools the agent calls, in order, with one-line Spanish descriptions
# for the "Agente listo" preview card.
AGENT_TOOLS: list[tuple[str, str]] = [
    ("get_informe_medico", "Lee el informe médico completo desde Notion."),
    ("get_poliza_paciente", "Obtiene la póliza vigente del paciente."),
    ("get_cobertura", "Consulta la regla de cobertura del procedimiento."),
    ("verificar_carencia", "Calcula si la póliza cumple el período de carencia."),
    ("validar_documentos", "Compara documentos requeridos vs adjuntos."),
    ("emitir_decision", "Escribe la decisión final en Notion."),
]


_SPANISH_MONTHS = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]


def fmt_date(iso: Optional[str]) -> str:
    """Format an ISO date string as `dd mmm yyyy` in Spanish (or `—` if empty)."""
    if not iso:
        return "—"
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d").date()
    except ValueError:
        return iso
    return f"{d.day:02d} {_SPANISH_MONTHS[d.month - 1]} {d.year}"


def calc_edad(fecha_nacimiento: Optional[str], today: Optional[date] = None) -> Optional[int]:
    """Return the age in completed years given an ISO birth date.

    `today` is overridable for tests; defaults to date.today().
    """
    if not fecha_nacimiento:
        return None
    try:
        born = datetime.strptime(fecha_nacimiento[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    ref = today or date.today()
    age = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
    return age if age >= 0 else None


def doc_label(code: str) -> str:
    """Look up a friendly Spanish label, falling back to the code itself."""
    return DOC_LABEL.get(code, code)


def decision_tone(decision: Optional[str]) -> str:
    """Map a decision label to a tone class — `good`, `bad`, `warn`, `neutral`."""
    if decision == "Aprobado":
        return "good"
    if decision == "Negado":
        return "bad"
    if decision == "Documentos_Faltantes":
        return "warn"
    return "neutral"


def decision_emblem(decision: Optional[str]) -> str:
    """Return a single character emblem for the verdict hero."""
    return {
        "Aprobado": "✓",
        "Negado": "✕",
        "Documentos_Faltantes": "!",
    }.get(decision or "", "?")


def parse_carencia_check(trace: list[Any]) -> Optional[dict[str, Any]]:
    """Pull the verificar_carencia output from a trace, if present.

    Accepts both TraceEntry dataclasses and plain dicts so this helper is
    reusable across the live API response and mock fixtures.
    """
    for entry in trace:
        tool = _entry_field(entry, "tool")
        if tool == "verificar_carencia":
            output = _entry_field(entry, "output") or {}
            if not isinstance(output, dict):
                return None
            return {
                "dias_transcurridos": output.get("dias_transcurridos"),
                "dias_requeridos": output.get("dias_requeridos"),
                "dias_faltantes": output.get("dias_faltantes"),
                "cumple": output.get("cumple"),
            }
    return None


def parse_documentos_check(trace: list[Any]) -> Optional[dict[str, Any]]:
    """Pull the validar_documentos output from a trace, if present."""
    for entry in trace:
        tool = _entry_field(entry, "tool")
        if tool == "validar_documentos":
            input_ = _entry_field(entry, "input") or {}
            output = _entry_field(entry, "output") or {}
            if not isinstance(output, dict):
                return None
            return {
                "requeridos": list(input_.get("documentos_requeridos") or []),
                "adjuntos": list(input_.get("documentos_adjuntos") or []),
                "faltantes": list(output.get("documentos_faltantes") or []),
                "completo": output.get("completo"),
            }
    return None


def entry_field(entry: Any, name: str) -> Any:
    """Read a field off a TraceEntry-shaped object — accepts dataclass OR dict.

    Public so resultado / procesando / future screens stop duplicating the
    `entry.tool if hasattr(...) else entry.get(...)` pattern.
    """
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


# Backward-compat alias; existing call sites in this module still use _entry_field.
_entry_field = entry_field
