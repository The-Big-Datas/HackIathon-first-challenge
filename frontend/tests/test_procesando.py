"""Tests for the pure helper inside screens/procesando.py."""

from __future__ import annotations

from screens.procesando import _match_placeholders


def test_match_full_six_tool_trace():
    trace = [
        {"tool": "get_informe_medico", "output": {}},
        {"tool": "get_poliza_paciente", "output": {}},
        {"tool": "get_cobertura", "output": {}},
        {"tool": "verificar_carencia", "output": {}},
        {"tool": "validar_documentos", "output": {}},
        {"tool": "emitir_decision", "output": {}},
    ]
    pairs = _match_placeholders(trace)
    assert [idx for idx, _ in pairs] == [0, 1, 2, 3, 4, 5]


def test_match_early_halt_on_carencia():
    """Agent halts on cobertura/carencia and emits decision early."""
    trace = [
        {"tool": "get_informe_medico", "output": {}},
        {"tool": "get_poliza_paciente", "output": {}},
        {"tool": "get_cobertura", "output": {}},
        {"tool": "verificar_carencia", "output": {"cumple": False}},
        {"tool": "emitir_decision", "output": {"ok": True}},
    ]
    pairs = _match_placeholders(trace)
    indices = [idx for idx, _ in pairs]
    assert indices == [0, 1, 2, 3, 5]  # validar_documentos (idx 4) skipped
    assert len(pairs) == 5


def test_match_drops_unknown_tool():
    trace = [
        {"tool": "get_informe_medico", "output": {}},
        {"tool": "mystery_tool", "output": {}},
        {"tool": "emitir_decision", "output": {}},
    ]
    pairs = _match_placeholders(trace)
    assert [idx for idx, _ in pairs] == [0, 5]


def test_match_handles_dataclass_like_entries():
    class FakeEntry:
        def __init__(self, tool, output):
            self.tool = tool
            self.output = output

    trace = [FakeEntry("get_informe_medico", {}), FakeEntry("emitir_decision", {})]
    pairs = _match_placeholders(trace)
    assert [idx for idx, _ in pairs] == [0, 5]


def test_match_empty_trace():
    assert _match_placeholders([]) == []


def test_match_entry_without_tool_field():
    trace = [{"output": "no tool field"}, {"tool": "", "output": {}}, {"tool": "emitir_decision", "output": {}}]
    pairs = _match_placeholders(trace)
    assert [idx for idx, _ in pairs] == [5]
