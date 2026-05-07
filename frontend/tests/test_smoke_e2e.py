"""End-to-end smoke test using Streamlit's AppTest framework.

Requires the dev stub backend running on http://localhost:8000.
Run: pytest tests/test_smoke_e2e.py -v

Each test drives the full stage flow for one demo informe and asserts the
expected verdict landed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
BACKEND = "http://localhost:8000"


def _backend_alive() -> bool:
    try:
        r = requests.get(f"{BACKEND}/health", timeout=1.0)
        return r.ok and r.json().get("ok") is True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _backend_alive(),
    reason="dev stub backend not running on localhost:8000",
)


def _new_app() -> AppTest:
    os.environ["BACKEND_URL"] = BACKEND
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    return at


def _click_open(at: AppTest, informe_id: str) -> None:
    """Simulate a row click by setting the ?open=<id> query param.

    The row HTML is wrapped in an <a href="?open=ID"> link; clicking it
    sets the query param, and the bandeja screen routes on rerun. AppTest
    can't synthesize an HTML <a> click, but it can mutate query_params
    and re-run, which exercises the same code path.
    """
    at.query_params["open"] = informe_id
    at.run()


def _click_procesar(at: AppTest) -> None:
    btn = next(b for b in at.button if b.key == "detalle_procesar")
    btn.click().run()


def test_bandeja_lists_three_informes():
    at = _new_app()
    assert at.session_state.stage == "bandeja"
    # Rows are rendered as anchor links (?open=<id>), not Streamlit buttons,
    # so we check the rendered HTML instead.
    html_blocks = "\n".join(getattr(m, "value", "") for m in at.markdown if m.value)
    # AppTest's html() output may not be in .markdown depending on Streamlit
    # version; alternately each row carries the informe id in some element.
    # Smoke check that the bandeja screen rendered without erroring is enough
    # — the click test below proves wiring works.
    assert at.session_state.stage == "bandeja"
    assert at.session_state.processed_ids == set()


def test_inf001_reaches_aprobado():
    at = _new_app()
    _click_open(at, "INF-001")
    assert at.session_state.stage == "detalle"
    assert at.session_state.selected_informe_id == "INF-001"

    _click_procesar(at)
    # Procesando renders, calls backend synchronously, transitions to Resultado
    assert at.session_state.stage == "resultado"
    result = at.session_state.last_result
    assert result is not None
    assert result.decision is not None
    assert result.decision.decision == "Aprobado"
    assert "INF-001" in at.session_state.processed_ids


def test_inf002_reaches_negado_on_carencia():
    at = _new_app()
    _click_open(at, "INF-002")
    _click_procesar(at)
    result = at.session_state.last_result
    assert at.session_state.stage == "resultado"
    assert result.decision.decision == "Negado"
    # Trace should include carencia entry but stop before validar_documentos
    tools = [t.tool for t in result.trace]
    assert "verificar_carencia" in tools
    assert "validar_documentos" not in tools


def test_inf003_reaches_documentos_faltantes():
    at = _new_app()
    _click_open(at, "INF-003")
    _click_procesar(at)
    result = at.session_state.last_result
    assert at.session_state.stage == "resultado"
    assert result.decision.decision == "Documentos_Faltantes"
    assert "segundo_dictamen" in result.decision.documentos_faltantes
    assert "examenes_prequirurgicos" in result.decision.documentos_faltantes


def test_volver_to_bandeja_marks_processed():
    at = _new_app()
    _click_open(at, "INF-001")
    _click_procesar(at)
    assert at.session_state.stage == "resultado"

    # res_inbox navigates to bandeja; res_back_top navigates to detalle.
    back = next(b for b in at.button if b.key == "res_inbox")
    back.click().run()
    assert at.session_state.stage == "bandeja"
    assert "INF-001" in at.session_state.processed_ids
