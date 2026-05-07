"""Session state initialization and stage transition helpers.

All access to st.session_state from screens routes through this module.
Pure read helpers (is_processed, processed_count) are testable without
the streamlit runtime.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal

import streamlit as st

Stage = Literal["bandeja", "detalle", "procesando", "resultado"]

DEFAULTS: dict[str, Any] = {
    "stage": "bandeja",
    "selected_informe_id": None,
    "last_result": None,
    "processed_ids": None,  # populated as set() at init time
    "last_error": None,
}


def init_session() -> None:
    """Populate default session keys idempotently."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = set() if key == "processed_ids" else value


def _set_stage(stage: Stage, **updates: Any) -> None:
    st.session_state.stage = stage
    st.session_state.last_error = None
    for key, value in updates.items():
        st.session_state[key] = value


def go_to_bandeja() -> None:
    _set_stage("bandeja", selected_informe_id=None)
    st.rerun()


def go_to_detalle(informe_id: str) -> None:
    _set_stage("detalle", selected_informe_id=informe_id)
    st.rerun()


def go_to_procesando(informe_id: str) -> None:
    _set_stage("procesando", selected_informe_id=informe_id, last_result=None)
    st.rerun()


def go_to_resultado(result: Any) -> None:
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
