"""Regression tests for styles.inject(). Bugs this guards against:

1. Using ``st.html`` instead of ``st.markdown(unsafe_allow_html=True)``: in
   Streamlit 1.39 ``st.html`` strips ``<style>`` tag content via DOMPurify,
   leaving the tag in the DOM but empty.
2. Failing to sanitize CSS for markdown's HTML-block rules: ``*`` chars in
   selectors and comments get consumed as italic markers, and blank lines
   close the HTML block early. Both silently truncate the stylesheet.
3. Guarding ``inject()`` with a session-state flag: Streamlit's element-tree
   diff drops elements that aren't re-emitted on the current run, so guarding
   would cause the CSS to disappear on every screen transition after the
   first render.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

import styles


class _FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def fake_st():
    with patch("styles.st") as mock_st:
        mock_st.session_state = _FakeSessionState()
        mock_st.markdown = MagicMock()
        mock_st.html = MagicMock()
        yield mock_st


def test_inject_uses_st_markdown_not_st_html(fake_st):
    """st.markdown preserves <style> content; st.html does not."""
    styles.inject()
    fake_st.markdown.assert_called_once()
    fake_st.html.assert_not_called()


def test_inject_passes_unsafe_allow_html_true(fake_st):
    styles.inject()
    args, kwargs = fake_st.markdown.call_args
    assert kwargs.get("unsafe_allow_html") is True


def test_inject_payload_contains_style_tag(fake_st):
    styles.inject()
    payload = fake_st.markdown.call_args.args[0]
    assert "<style>" in payload
    assert "</style>" in payload
    assert "--brand: #1763d1" in payload
    assert "Inter Tight" in payload


def test_inject_runs_on_every_call(fake_st):
    """Streamlit's element-tree diff drops elements not re-emitted each run."""
    styles.inject()
    styles.inject()
    styles.inject()
    assert fake_st.markdown.call_count == 3


def test_sanitizer_removes_all_asterisks():
    """Any ``*`` left in the CSS truncates the rule cascade silently."""
    sanitized = styles._sanitize_css_for_markdown(styles.CSS)
    assert "*" not in sanitized


def test_sanitizer_strips_block_comments():
    """CSS comments use ``/* */`` which markdown's italic rules eat."""
    sanitized = styles._sanitize_css_for_markdown(styles.CSS)
    assert "/*" not in sanitized
    assert "*/" not in sanitized


def test_sanitizer_collapses_blank_lines():
    """CommonMark closes <style> HTML blocks at the first blank line."""
    sanitized = styles._sanitize_css_for_markdown(styles.CSS)
    assert "\n\n" not in sanitized


def test_sanitizer_preserves_design_tokens():
    sanitized = styles._sanitize_css_for_markdown(styles.CSS)
    assert "--brand: #1763d1" in sanitized
    assert "@keyframes" in sanitized
    assert ".inbox-row" in sanitized
    assert "stSidebar" in sanitized
    assert "verdict-hero" in sanitized
    assert "hdr-btn" in sanitized


def test_sanitizer_rewrites_class_attribute_selector():
    """[class*="st-"] gets rewritten to [class^="st-"] (asterisk-free)."""
    sanitized = styles._sanitize_css_for_markdown(styles.CSS)
    assert '[class*="st-"]' not in sanitized
    assert '[class^="st-"]' in sanitized
