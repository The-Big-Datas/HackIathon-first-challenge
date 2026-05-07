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
