"""Tests for frontend/api.py — covers happy paths and every BackendError kind."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

import api


@pytest.fixture(autouse=True)
def _fixed_backend(monkeypatch):
    monkeypatch.setenv("BACKEND_URL", "http://fake-backend:8000")


def _mock_response(*, ok=True, status=200, json_data=None, text=""):
    resp = MagicMock()
    resp.ok = ok
    resp.status_code = status
    resp.text = text
    if json_data is None:
        resp.json.side_effect = json.JSONDecodeError("expected JSON", "", 0)
    else:
        resp.json.return_value = json_data
    return resp


def test_fetch_informes_happy_path():
    sample = [
        {"id_informe": "INF-001", "descripcion_procedimiento": "Apendicectomía", "hospital": "Metropolitano"},
        {"id_informe": "INF-002", "descripcion_procedimiento": "Bariátrica", "hospital": "Vozandes"},
        {"id_informe": "INF-003", "descripcion_procedimiento": "Colecistectomía", "hospital": "Alcívar"},
    ]
    with patch("api.requests.request", return_value=_mock_response(json_data=sample)):
        items = api.fetch_informes()
    assert len(items) == 3
    assert items[0].id_informe == "INF-001"
    assert items[1].descripcion_procedimiento == "Bariátrica"
    assert items[2].hospital == "Alcívar"


def test_procesar_informe_happy_path():
    payload = {
        "trace": [
            {"tool": "get_informe_medico", "input": {"informe_id": "INF-001"}, "output": {"ok": True}},
            {"tool": "emitir_decision", "input": {}, "output": {"ok": True}},
        ],
        "final_text": "Aprobado.",
        "decision": {
            "decision": "Aprobado",
            "justificacion": "Cumple",
            "clausula_aplicada": "2.1",
            "documentos_faltantes": [],
        },
    }
    with patch("api.requests.request", return_value=_mock_response(json_data=payload)):
        result = api.procesar_informe("INF-001")
    assert len(result.trace) == 2
    assert result.trace[0].tool == "get_informe_medico"
    assert result.final_text == "Aprobado."
    assert result.decision is not None
    assert result.decision.decision == "Aprobado"
    assert result.decision.documentos_faltantes == []


def test_procesar_informe_with_null_decision_does_not_raise():
    payload = {"trace": [], "final_text": "agente no emitió", "decision": None}
    with patch("api.requests.request", return_value=_mock_response(json_data=payload)):
        result = api.procesar_informe("INF-XYZ")
    assert result.decision is None
    assert result.final_text == "agente no emitió"


def test_http_error_raises_backend_error():
    resp = _mock_response(ok=False, status=500, json_data={}, text="boom")
    with patch("api.requests.request", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informes()
    err = exc_info.value
    assert err.kind == "http"
    assert err.status == 500
    assert "500" in err.message


def test_connection_error_raises_network_error():
    with patch("api.requests.request", side_effect=requests.exceptions.ConnectionError("refused")):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informes()
    assert exc_info.value.kind == "network"


def test_timeout_raises_timeout_error():
    with patch("api.requests.request", side_effect=requests.exceptions.Timeout("slow")):
        with pytest.raises(api.BackendError) as exc_info:
            api.procesar_informe("INF-001")
    assert exc_info.value.kind == "timeout"


def test_malformed_json_raises_decode_error():
    resp = _mock_response(json_data=None)  # json() will raise JSONDecodeError
    with patch("api.requests.request", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informes()
    assert exc_info.value.kind == "decode"


def test_fetch_informes_rejects_non_list_payload():
    resp = _mock_response(json_data={"not": "a list"})
    with patch("api.requests.request", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informes()
    assert exc_info.value.kind == "decode"
    assert "list" in exc_info.value.message


# ============================================================================
# fetch_informe_detail
# ============================================================================

def test_fetch_informe_detail_happy_path():
    payload = {
        "id_informe": "INF-001",
        "paciente_cedula": "0000000001",
        "paciente_nombre": "[DEMO] Paciente Uno",
        "procedimiento_cpt": "44970",
    }
    with patch("api.requests.get", return_value=_mock_response(json_data=payload)):
        d = api.fetch_informe_detail("INF-001")
    assert d is not None
    assert d.id_informe == "INF-001"
    assert d.paciente_nombre == "[DEMO] Paciente Uno"


def test_fetch_informe_detail_404_returns_none():
    """The endpoint may not be implemented; 404 → None lets the screen fall
    back to the slim list view rather than raising."""
    resp = _mock_response(ok=False, status=404, json_data={"detail": "not found"}, text="not found")
    with patch("api.requests.get", return_value=resp):
        out = api.fetch_informe_detail("INF-XYZ")
    assert out is None


def test_fetch_informe_detail_500_raises_http():
    resp = _mock_response(ok=False, status=500, json_data={}, text="boom")
    with patch("api.requests.get", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informe_detail("INF-001")
    assert exc_info.value.kind == "http"


def test_fetch_informe_detail_timeout_raises():
    with patch("api.requests.get", side_effect=requests.exceptions.Timeout("slow")):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informe_detail("INF-001")
    assert exc_info.value.kind == "timeout"


def test_fetch_informe_detail_connection_error_raises():
    with patch("api.requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informe_detail("INF-001")
    assert exc_info.value.kind == "network"


def test_fetch_informe_detail_decode_error_raises():
    resp = _mock_response(json_data=None)
    with patch("api.requests.get", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informe_detail("INF-001")
    assert exc_info.value.kind == "decode"


def test_fetch_informe_detail_non_dict_payload_raises():
    resp = _mock_response(json_data=["not", "an", "object"])
    with patch("api.requests.get", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informe_detail("INF-001")
    assert exc_info.value.kind == "decode"


# ============================================================================
# fetch_cobertura — distinguishes 404-no-rule from network errors
# ============================================================================

def test_fetch_cobertura_happy_path():
    payload = {"cubierto": True, "dias_carencia": 30, "documentos_requeridos": ["a", "b"]}
    with patch("api.requests.get", return_value=_mock_response(json_data=payload)):
        c = api.fetch_cobertura("44970", "plan_premium")
    assert c is not None
    assert c.cubierto is True
    assert c.dias_carencia == 30


def test_fetch_cobertura_404_with_no_rule_payload_returns_cobertura():
    """The backend may return a 404 with a 'cubierto: False' body to signal
    'no rule for this plan'. That should deserialize, not be dropped."""
    payload = {"cubierto": False, "motivo": "no rule"}
    resp = _mock_response(ok=False, status=404, json_data=payload, text="...")
    with patch("api.requests.get", return_value=resp):
        c = api.fetch_cobertura("99999", "plan_basico")
    assert c is not None
    assert c.cubierto is False


def test_fetch_cobertura_404_without_payload_returns_none():
    resp = _mock_response(ok=False, status=404, json_data={"detail": "not found"}, text="not found")
    with patch("api.requests.get", return_value=resp):
        out = api.fetch_cobertura("99999", "plan_basico")
    assert out is None


def test_fetch_cobertura_network_error_raises_not_silent_none():
    """Critical: network errors must NOT be silently swallowed as None.
    Otherwise the UI can't distinguish 'no rule' from 'backend down'.
    This was a P1 finding from the code review."""
    with patch("api.requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_cobertura("44970", "plan_premium")
    assert exc_info.value.kind == "network"


def test_fetch_cobertura_timeout_raises():
    with patch("api.requests.get", side_effect=requests.exceptions.Timeout("slow")):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_cobertura("44970", "plan_premium")
    assert exc_info.value.kind == "timeout"


def test_fetch_cobertura_500_raises_http():
    resp = _mock_response(ok=False, status=500, json_data={}, text="boom")
    with patch("api.requests.get", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_cobertura("44970", "plan_premium")
    assert exc_info.value.kind == "http"


def test_fetch_cobertura_empty_inputs_return_none():
    out_a = api.fetch_cobertura("", "plan_premium")
    out_b = api.fetch_cobertura("44970", "")
    assert out_a is None
    assert out_b is None


# ============================================================================
# Decision normalization
# ============================================================================

def test_decision_normalization_canonical_values():
    for v in ("Aprobado", "Negado", "Documentos_Faltantes"):
        out = api._normalize_decision(v)
        assert out == v


def test_decision_normalization_case_drift():
    """Casing variants should normalize to the canonical decision so the
    verdict hero color resolves correctly."""
    assert api._normalize_decision("aprobado") == "Aprobado"
    assert api._normalize_decision("APROBADO") == "Aprobado"
    assert api._normalize_decision("documentos faltantes") == "Documentos_Faltantes"
    assert api._normalize_decision("Documentos faltantes") == "Documentos_Faltantes"


def test_decision_normalization_unknown_falls_back():
    assert api._normalize_decision("") == "Unknown"
    assert api._normalize_decision("Mystery") == "Unknown"


def test_decision_from_dict_normalizes():
    d = api.Decision.from_dict({"decision": "aprobado"})
    assert d.decision == "Aprobado"


# ============================================================================
# PII scrubbing in error messages
# ============================================================================

def test_http_error_scrubs_pii_from_body():
    """Error bodies render in the user-visible debug expander; cedulas
    and decision IDs must be redacted before they reach the UI."""
    resp = _mock_response(ok=False, status=500, json_data={}, text="error: cedula 1234567890 in DEC-INF-001-APR")
    with patch("api.requests.request", return_value=resp):
        with pytest.raises(api.BackendError) as exc_info:
            api.fetch_informes()
    assert "1234567890" not in exc_info.value.message
    assert "DEC-INF-001-APR" not in exc_info.value.message
    assert "REDACTED" in exc_info.value.message


# ============================================================================
# ProcesarResponse defensive shape handling
# ============================================================================

def test_procesar_response_filters_non_dict_trace_entries():
    """If the backend ever returns trace items that aren't dicts (string,
    null), they should be dropped silently, not raise AttributeError."""
    payload = {
        "trace": [
            {"tool": "get_informe_medico", "input": {}, "output": {}},
            "not a dict",
            None,
            {"tool": "emitir_decision", "input": {}, "output": {}},
        ],
        "final_text": "",
        "decision": None,
    }
    with patch("api.requests.request", return_value=_mock_response(json_data=payload)):
        result = api.procesar_informe("INF-001")
    assert len(result.trace) == 2  # only the two dict entries survive
    assert result.trace[0].tool == "get_informe_medico"
    assert result.trace[1].tool == "emitir_decision"


def test_procesar_response_empty_decision_dict_creates_decision():
    """{} is a meaningful payload — decision present but unfilled.
    Distinguish from None/missing → decision absent."""
    payload = {"trace": [], "final_text": "", "decision": {}}
    with patch("api.requests.request", return_value=_mock_response(json_data=payload)):
        result = api.procesar_informe("INF-001")
    assert result.decision is not None
    assert result.decision.decision == "Unknown"  # normalized empty


def test_procesar_response_null_decision_is_none():
    payload = {"trace": [], "final_text": "", "decision": None}
    with patch("api.requests.request", return_value=_mock_response(json_data=payload)):
        result = api.procesar_informe("INF-001")
    assert result.decision is None
