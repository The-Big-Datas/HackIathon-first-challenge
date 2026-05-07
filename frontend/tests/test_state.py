"""Tests for frontend/state.py — pure helpers and init_session idempotency."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

import state


class _FakeSessionState(dict):
    """Dict that also supports attribute access, like streamlit.session_state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def fake_session():
    fake = _FakeSessionState()
    with patch("state.st") as mock_st:
        mock_st.session_state = fake
        yield fake


def test_init_session_populates_defaults(fake_session):
    state.init_session()
    assert fake_session["stage"] == "bandeja"
    assert fake_session["selected_informe_id"] is None
    assert fake_session["last_result"] is None
    assert fake_session["last_error"] is None
    assert isinstance(fake_session["processed_ids"], set)
    assert fake_session["processed_ids"] == set()


def test_init_session_is_idempotent(fake_session):
    state.init_session()
    fake_session["processed_ids"].add("INF-001")
    state.init_session()  # second call — must not clobber existing
    assert fake_session["processed_ids"] == {"INF-001"}


def test_mark_processed(fake_session):
    state.init_session()
    state.mark_processed("INF-001")
    assert "INF-001" in fake_session["processed_ids"]
    state.mark_processed("INF-002")
    assert fake_session["processed_ids"] == {"INF-001", "INF-002"}


def test_mark_processed_ignores_empty(fake_session):
    state.init_session()
    state.mark_processed("")
    state.mark_processed(None)  # type: ignore[arg-type]
    assert fake_session["processed_ids"] == set()


def test_is_processed_pure_helper():
    assert state.is_processed({"INF-001", "INF-002"}, "INF-001") is True
    assert state.is_processed({"INF-001"}, "INF-002") is False
    assert state.is_processed(set(), "INF-001") is False


def test_processed_count_pure_helper():
    assert state.processed_count({"INF-001", "INF-003"}, ["INF-001", "INF-002", "INF-003"]) == 2
    assert state.processed_count(set(), ["INF-001", "INF-002"]) == 0
    assert state.processed_count({"INF-001"}, []) == 0
    # Items in processed_ids but no longer in the live list should not count
    assert state.processed_count({"INF-OLD"}, ["INF-001", "INF-002"]) == 0


def test_set_stage_clears_last_error(fake_session):
    state.init_session()
    fake_session["last_error"] = "stale"
    state._set_stage("detalle", selected_informe_id="INF-001")
    assert fake_session["stage"] == "detalle"
    assert fake_session["last_error"] is None
    assert fake_session["selected_informe_id"] == "INF-001"


def test_go_to_helpers_call_rerun(fake_session):
    state.init_session()
    with patch("state.st.rerun") as rerun:
        state.go_to_detalle("INF-001")
    assert fake_session["stage"] == "detalle"
    assert fake_session["selected_informe_id"] == "INF-001"
    rerun.assert_called_once()


# ============================================================================
# is_valid_informe_id — query-param allowlist
# ============================================================================


def test_is_valid_informe_id_accepts_canonical_ids():
    assert state.is_valid_informe_id("INF-001")
    assert state.is_valid_informe_id("INF_002")
    assert state.is_valid_informe_id("abc123")


def test_is_valid_informe_id_rejects_path_traversal():
    """Path-injection vector: ?open=../admin or ?open=foo/../bar must NOT
    pass validation. P0 finding from the security review."""
    assert not state.is_valid_informe_id("../admin")
    assert not state.is_valid_informe_id("../../etc/passwd")
    assert not state.is_valid_informe_id("foo/bar")


def test_is_valid_informe_id_rejects_oversize():
    """10MB strings shouldn't persist in session_state."""
    assert not state.is_valid_informe_id("A" * 65)


def test_is_valid_informe_id_rejects_unicode_tricks():
    assert not state.is_valid_informe_id("INF-001‮")  # RTL override
    assert not state.is_valid_informe_id("INF-001%00")
    assert not state.is_valid_informe_id("INF-001 ")  # trailing space


def test_is_valid_informe_id_rejects_empty_and_none():
    assert not state.is_valid_informe_id("")
    assert not state.is_valid_informe_id(None)  # type: ignore[arg-type]


def test_go_to_detalle_refuses_invalid_id(fake_session):
    """The transition helper itself enforces the allowlist as defense-in-depth."""
    state.init_session()
    with patch("state.st.rerun") as rerun:
        state.go_to_detalle("../admin")
    # Should NOT have transitioned
    assert fake_session["stage"] == "bandeja"
    rerun.assert_not_called()


# ============================================================================
# Per-id decision tracking — fixes the wrong-status-on-multi-informe bug
# ============================================================================


class _FakeResult:
    """Minimal stand-in for ProcesarResponse with a Decision."""

    def __init__(self, decision_value):
        class _D:
            decision = decision_value
        self.decision = _D() if decision_value else None


def test_decision_counts_per_informe_not_global():
    """The bug: stat tiles read from a single global last_result, so processing
    INF-001=Aprobado then INF-002=Negado made BOTH rows display Negado.
    Fix: count from results_by_id keyed by informe_id."""
    results = {
        "INF-001": _FakeResult("Aprobado"),
        "INF-002": _FakeResult("Negado"),
        "INF-003": _FakeResult("Documentos_Faltantes"),
    }
    counts = state.decision_counts(results, ["INF-001", "INF-002", "INF-003"])
    assert counts == {"Aprobado": 1, "Negado": 1, "Documentos_Faltantes": 1}


def test_decision_counts_ignores_stale_ids():
    """Results for since-deleted informes should not inflate the counters."""
    results = {
        "INF-001": _FakeResult("Aprobado"),
        "INF-OLD": _FakeResult("Aprobado"),  # not in live list
    }
    counts = state.decision_counts(results, ["INF-001", "INF-002"])
    assert counts["Aprobado"] == 1


def test_decision_counts_empty_inputs():
    assert state.decision_counts({}, []) == {"Aprobado": 0, "Negado": 0, "Documentos_Faltantes": 0}
    assert state.decision_counts(None, ["INF-001"]) == {"Aprobado": 0, "Negado": 0, "Documentos_Faltantes": 0}


def test_decision_counts_skips_results_with_no_decision():
    results = {"INF-001": _FakeResult(None)}
    counts = state.decision_counts(results, ["INF-001"])
    assert counts == {"Aprobado": 0, "Negado": 0, "Documentos_Faltantes": 0}
