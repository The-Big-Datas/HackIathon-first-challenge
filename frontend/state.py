"""Session state initialization and stage transition helpers.

All access to st.session_state from screens should route through this module,
which keeps the per-session shape testable and centralized.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Literal, Optional

import streamlit as st

Stage = Literal["bandeja", "detalle", "procesando", "resultado"]

# Allowlist for ?open=<id>: alphanum, dash, underscore. Tightens the surface
# against path traversal / oversize payloads / unicode tricks before the value
# reaches state or the network layer.
_INFORME_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

DEFAULTS: dict[str, Any] = {
    "stage": "bandeja",
    "selected_informe_id": None,
    # `last_result` is kept for backward compat; new code reads results_by_id.
    "last_result": None,
    # Per-informe decision storage: id -> ProcesarResponse. Replaces the
    # single-result-shared-by-all-rows shape that produced wrong status chips
    # in the inbox after multiple processing runs.
    "results_by_id": None,
    "processed_ids": None,
    "last_error": None,
}


def init_session() -> None:
    """Populate default session keys idempotently."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            if key == "processed_ids":
                st.session_state[key] = set()
            elif key == "results_by_id":
                st.session_state[key] = {}
            else:
                st.session_state[key] = value


def is_valid_informe_id(value: Optional[str]) -> bool:
    """True when value is a safe informe identifier.

    Centralized so any caller (not just bandeja's query-param click handler)
    gets the same allowlist.
    """
    if not value or not isinstance(value, str):
        return False
    return _INFORME_ID_PATTERN.fullmatch(value) is not None


def _set_stage(stage: Stage, **updates: Any) -> None:
    st.session_state.stage = stage
    st.session_state.last_error = None
    for key, value in updates.items():
        st.session_state[key] = value


def go_to_bandeja() -> None:
    _set_stage("bandeja", selected_informe_id=None)
    st.rerun()


def go_to_detalle(informe_id: str) -> None:
    if not is_valid_informe_id(informe_id):
        # Refuse the navigation rather than passing junk down to the API client.
        st.session_state.last_error = "Identificador inválido."
        return
    _set_stage("detalle", selected_informe_id=informe_id)
    st.rerun()


def go_to_procesando(informe_id: str) -> None:
    if not is_valid_informe_id(informe_id):
        st.session_state.last_error = "Identificador inválido."
        return
    _set_stage("procesando", selected_informe_id=informe_id, last_result=None)
    st.rerun()


def go_to_resultado(result: Any) -> None:
    """Stores the result and transitions to resultado stage.

    Also writes to results_by_id keyed by selected_informe_id so the bandeja
    stat tiles + per-row status chip can reflect every processed run, not just
    the most recent one.
    """
    informe_id = st.session_state.get("selected_informe_id")
    if informe_id and result is not None:
        results = st.session_state.results_by_id or {}
        results[informe_id] = result
        st.session_state.results_by_id = results
    _set_stage("resultado", last_result=result)
    st.rerun()


def mark_processed(informe_id: str) -> None:
    if informe_id:
        st.session_state.processed_ids.add(informe_id)


# Pure read helpers — testable without streamlit


def is_processed(processed_ids: Iterable[str], informe_id: str) -> bool:
    return informe_id in set(processed_ids)


def processed_count(processed_ids: Iterable[str], informe_ids: Iterable[str]) -> int:
    return len(set(processed_ids) & set(informe_ids))


def decision_counts(
    results_by_id: dict[str, Any], informe_ids: Iterable[str]
) -> dict[str, int]:
    """Count Aprobado/Negado/Documentos_Faltantes across the live informes.

    Iterates results_by_id and only counts entries whose key is in the
    current live informes list — stale results from since-deleted ids do
    not inflate the counters.
    """
    counts = {"Aprobado": 0, "Negado": 0, "Documentos_Faltantes": 0}
    live = set(informe_ids)
    for informe_id, result in (results_by_id or {}).items():
        if informe_id not in live:
            continue
        decision = getattr(getattr(result, "decision", None), "decision", None)
        if decision in counts:
            counts[decision] += 1
    return counts


def get_result_for(informe_id: str) -> Any:
    """Look up the stored ProcesarResponse for an informe id, or None."""
    results = st.session_state.get("results_by_id") or {}
    return results.get(informe_id)
