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
