"""Tests for frontend/utils.py — pure helpers."""

from __future__ import annotations

from datetime import date

import pytest

import utils


def test_calc_edad_before_birthday():
    assert utils.calc_edad("1985-05-12", today=date(2026, 5, 7)) == 40


def test_calc_edad_on_birthday():
    assert utils.calc_edad("1985-05-12", today=date(2026, 5, 12)) == 41


def test_calc_edad_day_after_birthday():
    assert utils.calc_edad("1985-05-12", today=date(2026, 5, 13)) == 41


def test_calc_edad_handles_none_and_empty():
    assert utils.calc_edad(None) is None
    assert utils.calc_edad("") is None


def test_calc_edad_handles_invalid_string():
    assert utils.calc_edad("not-a-date") is None


def test_fmt_date_spanish_format():
    assert utils.fmt_date("2024-05-07") == "07 may 2024"
    assert utils.fmt_date("2026-01-01") == "01 ene 2026"
    assert utils.fmt_date("2026-12-31") == "31 dic 2026"


def test_fmt_date_handles_none_and_empty():
    assert utils.fmt_date(None) == "—"
    assert utils.fmt_date("") == "—"


def test_fmt_date_handles_iso_with_time():
    assert utils.fmt_date("2024-05-07T12:00:00") == "07 may 2024"


def test_fmt_date_handles_invalid():
    assert utils.fmt_date("garbage") == "garbage"


def test_doc_label_known_codes():
    assert utils.doc_label("informe_quirurgico") == "Informe quirúrgico"
    assert utils.doc_label("examenes_prequirurgicos") == "Exámenes prequirúrgicos"
    assert utils.doc_label("segundo_dictamen") == "Segundo dictamen médico"
    assert utils.doc_label("exames_imagen") == "Exámenes de imagen"
    assert utils.doc_label("consentimiento") == "Consentimiento informado"


def test_doc_label_unknown_code_falls_back_to_code():
    assert utils.doc_label("unknown_thing") == "unknown_thing"


def test_decision_tone_mapping():
    assert utils.decision_tone("Aprobado") == "good"
    assert utils.decision_tone("Negado") == "bad"
    assert utils.decision_tone("Documentos_Faltantes") == "warn"
    assert utils.decision_tone(None) == "neutral"
    assert utils.decision_tone("Mystery") == "neutral"


def test_decision_emblem_mapping():
    assert utils.decision_emblem("Aprobado") == "✓"
    assert utils.decision_emblem("Negado") == "✕"
    assert utils.decision_emblem("Documentos_Faltantes") == "!"
    assert utils.decision_emblem(None) == "?"


def test_parse_carencia_check_with_entry():
    trace = [
        {"tool": "get_informe_medico", "input": {}, "output": {}},
        {"tool": "verificar_carencia", "input": {}, "output": {
            "cumple": False,
            "dias_transcurridos": 45,
            "dias_requeridos": 365,
            "dias_faltantes": 320,
        }},
    ]
    parsed = utils.parse_carencia_check(trace)
    assert parsed is not None
    assert parsed["cumple"] is False
    assert parsed["dias_transcurridos"] == 45
    assert parsed["dias_requeridos"] == 365


def test_parse_carencia_check_without_entry():
    trace = [{"tool": "get_informe_medico", "input": {}, "output": {}}]
    assert utils.parse_carencia_check(trace) is None


def test_parse_carencia_check_with_malformed_output():
    trace = [{"tool": "verificar_carencia", "input": {}, "output": "not a dict"}]
    assert utils.parse_carencia_check(trace) is None


def test_parse_documentos_check_with_faltantes():
    trace = [
        {"tool": "validar_documentos", "input": {
            "documentos_requeridos": ["a", "b", "c"],
            "documentos_adjuntos": ["a"],
        }, "output": {
            "completo": False,
            "documentos_faltantes": ["b", "c"],
        }},
    ]
    parsed = utils.parse_documentos_check(trace)
    assert parsed is not None
    assert parsed["faltantes"] == ["b", "c"]
    assert parsed["completo"] is False
    assert parsed["requeridos"] == ["a", "b", "c"]
    assert parsed["adjuntos"] == ["a"]


def test_parse_documentos_check_without_entry():
    trace = [{"tool": "verificar_carencia", "input": {}, "output": {}}]
    assert utils.parse_documentos_check(trace) is None


def test_parse_helpers_accept_dataclass_like_objects():
    """Sparingly, ensure the helpers work with anything that has .tool/.input/.output attrs."""

    class FakeEntry:
        def __init__(self, tool, input_, output):
            self.tool = tool
            self.input = input_
            self.output = output

    trace = [FakeEntry("verificar_carencia", {}, {"cumple": True, "dias_transcurridos": 100, "dias_requeridos": 30, "dias_faltantes": 0})]
    parsed = utils.parse_carencia_check(trace)
    assert parsed is not None
    assert parsed["cumple"] is True


def test_agent_tools_constant_has_six_entries():
    assert len(utils.AGENT_TOOLS) == 6
    names = [t[0] for t in utils.AGENT_TOOLS]
    assert names == [
        "get_informe_medico",
        "get_poliza_paciente",
        "get_cobertura",
        "verificar_carencia",
        "validar_documentos",
        "emitir_decision",
    ]
