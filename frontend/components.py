"""Reusable UI helpers — HTML-via-st.html for visuals, st.button for interaction."""

from __future__ import annotations

import html
import textwrap
from typing import Any, Callable, Iterable, Optional

import streamlit as st

from api import BackendError
from icons import icon


def render_html(content: str) -> None:
    """Render raw HTML preserving inline SVG.

    Uses ``st.markdown(unsafe_allow_html=True)`` instead of ``st.html`` because
    Streamlit's ``st.html`` runs DOMPurify with a config that strips ``<svg>``
    elements in current versions, which breaks the inline icon system.

    Dedents and drops blank lines so an empty f-string substitution
    can't leave a blank line that splits the HTML block — once split,
    the indented remainder is parsed as a code block and the tags
    render as escaped text.
    """
    dedented = textwrap.dedent(content)
    compact = "\n".join(line for line in dedented.splitlines() if line.strip())
    st.markdown(compact, unsafe_allow_html=True)


# ============================================================================
# Sidebar
# ============================================================================

def render_sidebar(active_stage: str, *, total_informes: int = 0) -> None:
    """Render the dark navy sidebar with brand + nav sections + user footer."""
    nav_op = [
        ("inbox", "Bandeja", "bandeja", str(total_informes)),
        ("check-shield", "Aprobadas", None, ""),
        ("alert", "Pendientes docs", None, ""),
        ("archive", "Histórico", None, ""),
    ]
    nav_cfg = [
        ("database", "Notion"),
        ("shield", "Reglas y cláusulas"),
        ("cpu", "Agente"),
        ("gear", "Ajustes"),
    ]

    op_html = ""
    bandeja_family = ("bandeja", "detalle", "procesando", "resultado")
    for ico, label, stage, count in nav_op:
        # Explicit parens — Bandeja highlights for any stage in the family,
        # other nav rows highlight only on exact stage match.
        active = (stage is not None and stage == active_stage) or (
            stage == "bandeja" and active_stage in bandeja_family
        )
        cls = "side-item active" if active else "side-item"
        count_html = f"<span class='count'>{count}</span>" if count else ""
        inner = f"{icon(ico, 16)}<span>{html.escape(label)}</span>{count_html}"
        # Items with a target stage become anchor links; clicks set ?nav=<stage>
        # which the app entry point reads to drive navigation.
        if stage is not None:
            op_html += (
                f"<a class='{cls}' href='?nav={stage}' target='_self'>{inner}</a>"
            )
        else:
            op_html += f"<div class='{cls} disabled'>{inner}</div>"

    cfg_html = "".join(
        f"<div class='side-item'>{icon(ico, 16)}<span>{html.escape(label)}</span></div>"
        for ico, label in nav_cfg
    )

    with st.sidebar:
        render_html(
            f"""
            <div class='side-brand'>
              <div class='mark'>{icon('shield-plus', 18, color='white')}</div>
              <div>
                <div class='name'>PreAuth</div>
                <div class='sub'>Viamatica · hackIAthon</div>
              </div>
            </div>

            <div class='side-sect'>Operación</div>
            <div class='side-list'>{op_html}</div>

            <div class='side-sect'>Configuración</div>
            <div class='side-list'>{cfg_html}</div>

            <div class='side-foot'>
              <div class='avatar'>VM</div>
              <div style='flex:1; min-width:0;'>
                <div class='who'>Auditor médico</div>
                <div class='role'>demo@viamatica</div>
              </div>
              {icon('logout', 14, color='#5d6c82')}
            </div>
            """
        )


# ============================================================================
# Topbar (renders inline at the top of the main content)
# ============================================================================

def topbar(*, breadcrumb: list[tuple[str, bool]], live_text: str = "Notion conectado · 6 DBs") -> None:
    """Render the topbar with breadcrumb, live pill, search/bell icons, avatar."""
    crumb_html = ""
    for i, (text, is_strong) in enumerate(breadcrumb):
        if i > 0:
            crumb_html += "<span class='sep'>/</span>"
        if is_strong:
            crumb_html += f"<b class='mono'>{html.escape(text)}</b>"
        else:
            crumb_html += html.escape(text)

    render_html(
        f"""
        <div class='topbar'>
          <div class='crumb'>{crumb_html}</div>
          <div class='spacer'></div>
          <span class='pill live'><span class='dot'></span>{html.escape(live_text)}</span>
          <span class='icon-btn'>{icon('search', 16)}</span>
          <span class='icon-btn'>{icon('bell', 16)}</span>
          <div class='topbar-avatar'>VM</div>
        </div>
        """
    )


# ============================================================================
# Page header inside a stage (h1 + sub + right-aligned actions)
# ============================================================================

def page_header(title: str, sub: str = "", *, badges_html: str = "", trailing_html: str = "") -> None:
    render_html(
        f"""
        <div style='display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:18px; gap:16px; flex-wrap:wrap;'>
          <div style='min-width:0;'>
            <div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>
              <h1 class='page-h1'>{html.escape(title)}</h1>
              {badges_html}
            </div>
            <div class='page-sub'>{sub}</div>
          </div>
          <div style='display:flex; gap:8px; align-items:center;'>{trailing_html}</div>
        </div>
        """
    )


# ============================================================================
# Stat tiles
# ============================================================================

def stat_tile(label: str, value: Any, *, tone: str = "brand", ico: str = "inbox") -> str:
    cls = f"stat-tile {tone}"
    return (
        f"<div class='{cls}'>"
        f"<div class='ico-sq'>{icon(ico, 18)}</div>"
        f"<div>"
        f"<div class='label'>{html.escape(label)}</div>"
        f"<div class='value'>{html.escape(str(value))}</div>"
        f"</div></div>"
    )


def stat_grid(tiles: Iterable[str]) -> None:
    render_html("<div class='stat-grid'>" + "".join(tiles) + "</div>")


# ============================================================================
# Badges
# ============================================================================

def badge(text: str, tone: str = "neutral", *, mono: bool = False) -> str:
    extra = " mono" if mono else ""
    return f"<span class='badge {tone}{extra}'>{html.escape(text)}</span>"


def status_chip(status: str) -> str:
    """Map a status string to a colored badge with a leading dot."""
    if status == "pendiente":
        return badge("Pendiente", "neutral")
    if status == "Aprobado":
        return "<span class='badge good'>● Aprobado</span>"
    if status == "Negado":
        return "<span class='badge bad'>● Negado</span>"
    if status == "Documentos_Faltantes":
        return "<span class='badge warn'>● Docs faltantes</span>"
    return badge(status, "neutral")


def urgency_chip(urgencia: str) -> str:
    tone = "bad" if urgencia == "Urgente" else "neutral"
    return f"<span class='badge {tone}' style='text-transform:none;'>{html.escape(urgencia or '—')}</span>"


def plan_badge(nivel: str, nombre: str = "") -> str:
    tone = "good" if nivel == "Premium" else ("brand" if nivel == "Estandar" else "neutral")
    text = nombre or nivel or "—"
    return f"<span class='badge {tone}'>{html.escape(text)}</span>"


# ============================================================================
# Cards (open / close so screens can mix HTML + Streamlit widgets inside)
# ============================================================================

def card_html(title: str, body_html: str, *, icon_name: str = "", meta_html: str = "") -> None:
    icon_html = (
        f"<span style='color: var(--ink-3);'>{icon(icon_name, 16)}</span>"
        if icon_name else ""
    )
    meta = f"<div class='meta'>{meta_html}</div>" if meta_html else ""
    render_html(
        f"""
        <div class='card'>
          <div class='card-h'>{icon_html}<h3>{html.escape(title)}</h3>{meta}</div>
          <div class='card-b'>{body_html}</div>
        </div>
        """
    )


def card_html_no_padding(title: str, inner_html: str, *, icon_name: str = "", meta_html: str = "") -> None:
    """Same as card_html but the inner HTML lives flush against the card header
    (no card-b padding) — used for tables that handle their own padding."""
    icon_html = (
        f"<span style='color: var(--ink-3);'>{icon(icon_name, 16)}</span>"
        if icon_name else ""
    )
    meta = f"<div class='meta'>{meta_html}</div>" if meta_html else ""
    render_html(
        f"""
        <div class='card'>
          <div class='card-h'>{icon_html}<h3>{html.escape(title)}</h3>{meta}</div>
          {inner_html}
        </div>
        """
    )


# ============================================================================
# KV blocks (Detalle)
# ============================================================================

def kv_block(label: str, value_html: str, *, sub_html: str = "") -> str:
    sub = f"<div class='sub'>{sub_html}</div>" if sub_html else ""
    return (
        f"<div class='kv'>"
        f"<div class='label'>{html.escape(label)}</div>"
        f"<div class='value'>{value_html}</div>"
        f"{sub}"
        f"</div>"
    )


def kv_grid(blocks: list[str]) -> str:
    return f"<div class='kv-grid'>{''.join(blocks)}</div>"


# ============================================================================
# Doc chip
# ============================================================================

def doc_chip(label: str, *, present: bool = True) -> str:
    cls = "doc-chip" if present else "doc-chip miss"
    icon_name = "doc-check" if present else "doc"
    return f"<span class='{cls}'>{icon(icon_name, 14)}{html.escape(label)}</span>"


# ============================================================================
# Error panel
# ============================================================================

def error_panel(err: BackendError, *, on_retry: Optional[Callable[[], None]] = None,
                key_prefix: str = "err") -> None:
    title_map = {
        "network": "No se pudo conectar al backend",
        "timeout": "El backend no respondió a tiempo",
        "http": f"El backend respondió con error{f' ({err.status})' if err.status else ''}",
        "decode": "Respuesta del backend con formato inválido",
    }
    title = title_map.get(err.kind, "Error inesperado")
    # Cold-wake hint for timeout errors — Render free-tier sleeps after 15min
    # of idle and takes ~30s to wake. Surface this so users don't read
    # "no respondió a tiempo" as "app is broken" and bounce.
    cold_wake_hint = (
        "<div style='font-size:12px; color:var(--ink-2); margin-top:8px; "
        "padding:8px 10px; background:var(--warn-bg); border-radius:6px;'>"
        "Si es la primera carga del día, el backend puede estar iniciándose. "
        "Espera unos segundos antes de reintentar."
        "</div>"
        if err.kind == "timeout" else ""
    )
    render_html(
        f"""
        <div class='card' style='border-color: rgba(192,57,43,.25);'>
          <div class='card-h' style='background: var(--bad-bg);'>
            <span style='color: var(--bad);'>{icon('alert', 16)}</span>
            <h3 style='color: var(--bad-ink);'>{html.escape(title)}</h3>
          </div>
          <div class='card-b'>
            <div style='font-size:13px; color:var(--ink-2); margin-bottom:6px;'>
              Backend: <span class='mono'>{html.escape(err.url)}</span>
            </div>
            {cold_wake_hint}
          </div>
        </div>
        """
    )
    with st.expander("Detalles técnicos"):
        # err.message is already PII-scrubbed at construction time (api._scrub_pii).
        st.code(err.message, language="text")
    if on_retry is not None:
        if st.button("Reintentar", key=f"{key_prefix}_retry", type="primary"):
            on_retry()


# code_block helper removed — was unused in production code.
