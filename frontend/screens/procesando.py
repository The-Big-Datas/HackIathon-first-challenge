"""Procesando screen — vertical-guide-line trace timeline + dark thinking panel."""

from __future__ import annotations

import html
import json
import time
from typing import Any, Optional

import streamlit as st

import api
import components
import state
from icons import icon

STEP_REVEAL_DELAY_S = 0.2

# Tool metadata mirroring the design's TOOL_META — labels, source captions
# and Spanish narration the thinking transcript reads off.
TOOL_META: dict[str, dict[str, str]] = {
    "get_informe_medico": {
        "icon": "doc",
        "label": "Leer informe médico",
        "source": "Notion · Informes_Medicos",
        "narr": "Voy a procesar la pre-autorización. Primero leo el informe completo desde Notion para identificar al paciente y el procedimiento.",
    },
    "get_poliza_paciente": {
        "icon": "shield",
        "label": "Obtener póliza del paciente",
        "source": "Notion · Asegurados, Pólizas",
        "narr": "Tengo la cédula del paciente. Ahora busco la póliza vigente para conocer el plan contratado.",
    },
    "get_cobertura": {
        "icon": "database",
        "label": "Consultar cobertura",
        "source": "Notion · Coberturas",
        "narr": "Conozco el plan. Consulto la regla de cobertura del CPT bajo este plan.",
    },
    "verificar_carencia": {
        "icon": "clock",
        "label": "Verificar período de carencia",
        "source": "Policy Engine · Python",
        "narr": "El procedimiento está cubierto. Verifico el período de carencia con cálculo determinístico — esto NO lo decido yo, lo calcula el policy engine.",
    },
    "validar_documentos": {
        "icon": "doc-check",
        "label": "Validar documentos adjuntos",
        "source": "Policy Engine · Python",
        "narr": "La carencia se cumple. Comparo documentos requeridos vs adjuntos del informe.",
    },
    "emitir_decision": {
        "icon": "flag",
        "label": "Emitir decisión final",
        "source": "Notion · Decisiones",
        "narr": "Tengo todos los chequeos. Emito la decisión final y la persisto en Notion para auditoría.",
    },
}

TOOL_ORDER = list(TOOL_META.keys())


def render(informe_id: Optional[str]) -> None:
    if not informe_id:
        st.warning("No se ha seleccionado ningún informe.")
        if st.button("← Volver a la bandeja", key="proc_back_noid"):
            state.go_to_bandeja()
        return

    # Capture the id at entry so we can detect cross-tab navigation away
    # from this stage during the long synchronous procesar call.
    entry_informe_id = informe_id

    # Page header — Volver button rendered BEFORE the blocking call so the user
    # has an escape hatch (best-effort: Streamlit can't truly cancel the POST,
    # but the click registers on the next rerun).
    head_cols = st.columns([1, 8], vertical_alignment="center")
    with head_cols[0]:
        if st.button("← Volver", key="proc_volver", use_container_width=True):
            state.go_to_bandeja()
            return
    with head_cols[1]:
        st.html(
            f"""
            <div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>
              <h1 class='page-h1'>Analizando informe</h1>
              <span class='badge brand mono'>{html.escape(informe_id)}</span>
              <span class='pill live'><span class='dot'></span>Agente activo</span>
            </div>
            <div class='page-sub'>Procesando con tool use directo · ~5–8 segundos · puede volver en cualquier momento</div>
            """
        )

    col_left, col_right = st.columns([14, 11], gap="medium")
    with col_left:
        timeline_inner = st.empty()
    with col_right:
        thinking_box = st.empty()
        telem_box = st.empty()
        neuro_box = st.empty()

    # Render initial placeholder timeline. The first tool slot starts in the
    # 'active' state with the pulsing dot so the page doesn't sit static
    # while the request is in flight.
    _render_timeline(timeline_inner, revealed_idxs=set(), trace=[], active_idx=0, elapsed=0.0, total_steps=len(TOOL_ORDER))
    _render_thinking(thinking_box, transcript_lines=[], active_idx=0)
    _render_telemetry(telem_box, tokens=0, elapsed=0.0, tools_done=0)
    _render_neuro_note(neuro_box)

    # Fire the actual backend call (5–15s)
    start = time.time()
    try:
        response = api.procesar_informe(informe_id)
    except api.BackendError as err:
        components.error_panel(err, on_retry=lambda: st.rerun(), key_prefix="proc_err")
        if st.button("← Volver a la bandeja", key="proc_back_err"):
            state.go_to_bandeja()
        return

    # Defensive race check: if the user navigated away during the long
    # synchronous call (cross-tab Procesar mid-flight scenario), don't
    # clobber their navigation by transitioning to resultado.
    current_id = st.session_state.get("selected_informe_id")
    current_stage = st.session_state.get("stage")
    if current_id != entry_informe_id or current_stage != "procesando":
        # User navigated away. Stash result for the original id (so the
        # bandeja stat tiles still update) and exit without st.rerun.
        results = st.session_state.get("results_by_id") or {}
        results[entry_informe_id] = response
        st.session_state.results_by_id = results
        state.mark_processed(entry_informe_id)
        return

    pairs = _match_placeholders(response.trace)

    # Dedup: keep first occurrence per placeholder index. Duplicate tool calls
    # in the trace would otherwise overwrite output in idx_to_entry, lose the
    # first call's data, double-count tokens, and double-append narration.
    seen_idxs: set[int] = set()
    deduped_pairs: list[tuple[int, Any]] = []
    for idx, entry in pairs:
        if idx in seen_idxs:
            continue
        seen_idxs.add(idx)
        deduped_pairs.append((idx, entry))

    # Reveal each step sequentially.
    # ORDERING FIX: render the timeline with active_idx=idx FIRST (so the
    # pulse-dot + 'Ejecutando…' badge is visible during the sleep), THEN add
    # to revealed and re-render in 'done' state. The previous order added to
    # revealed before rendering, which made the active-state branch dead code.
    revealed: set[int] = set()
    transcript: list[tuple[int, str]] = []
    tokens = 0
    ACTIVE_FRAME_S = STEP_REVEAL_DELAY_S * 0.6  # most of the budget on 'active'
    DONE_FRAME_S = STEP_REVEAL_DELAY_S * 0.4
    for idx, entry in deduped_pairs:
        narr = TOOL_META.get(_entry_tool(entry), {}).get("narr", "")
        if narr:
            transcript.append((idx, narr))

        # Active frame: pulse-dot + Ejecutando badge for this idx
        _render_timeline(
            timeline_inner,
            revealed_idxs=revealed,
            trace=response.trace,
            active_idx=idx,
            elapsed=time.time() - start,
            total_steps=len(TOOL_ORDER),
        )
        _render_thinking(thinking_box, transcript_lines=transcript, active_idx=idx)
        _render_telemetry(
            telem_box,
            tokens=tokens + 1500,
            elapsed=time.time() - start,
            tools_done=len(revealed),
        )
        time.sleep(ACTIVE_FRAME_S)

        # Done frame: now mark as completed
        revealed.add(idx)
        tokens += 1500
        _render_timeline(
            timeline_inner,
            revealed_idxs=revealed,
            trace=response.trace,
            active_idx=-1,
            elapsed=time.time() - start,
            total_steps=len(TOOL_ORDER),
        )
        time.sleep(DONE_FRAME_S)

    # Final state — no active step, all revealed
    final_elapsed = time.time() - start
    _render_timeline(
        timeline_inner,
        revealed_idxs=revealed,
        trace=response.trace,
        active_idx=-1,
        elapsed=final_elapsed,
        total_steps=len(TOOL_ORDER),
    )
    _render_thinking(thinking_box, transcript_lines=transcript, active_idx=-1)
    _render_telemetry(telem_box, tokens=tokens, elapsed=final_elapsed, tools_done=len(revealed))

    # Final defensive race check before clobbering navigation.
    current_id = st.session_state.get("selected_informe_id")
    current_stage = st.session_state.get("stage")
    if current_id != entry_informe_id or current_stage != "procesando":
        results = st.session_state.get("results_by_id") or {}
        results[entry_informe_id] = response
        st.session_state.results_by_id = results
        state.mark_processed(entry_informe_id)
        return

    state.mark_processed(informe_id)
    state.go_to_resultado(response)


def _match_placeholders(trace: list[Any]) -> list[tuple[int, Any]]:
    """Pure helper: map each trace entry to its placeholder index in order."""
    name_to_idx = {name: idx for idx, name in enumerate(TOOL_ORDER)}
    pairs: list[tuple[int, Any]] = []
    for entry in trace:
        tool = _entry_tool(entry)
        if not tool or tool not in name_to_idx:
            continue
        pairs.append((name_to_idx[tool], entry))
    return pairs


def _entry_tool(entry: Any) -> str:
    if isinstance(entry, dict):
        return entry.get("tool", "")
    return getattr(entry, "tool", "") or ""


def _entry_input(entry: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get("input", {}) or {}
    return getattr(entry, "input", {}) or {}


def _entry_output(entry: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get("output", None)
    return getattr(entry, "output", None)


def _render_timeline(
    box: Any,
    *,
    revealed_idxs: set[int],
    trace: list[Any],
    active_idx: int,
    elapsed: float,
    total_steps: int,
) -> None:
    # Find which trace entry maps to each tool index for the OK steps
    idx_to_entry: dict[int, Any] = {}
    for idx, entry in _match_placeholders(trace):
        idx_to_entry[idx] = entry

    parts: list[str] = []
    parts.append("<div class='timeline-wrap'>")
    parts.append("<div class='timeline-line'></div>")

    for i, name in enumerate(TOOL_ORDER):
        meta = TOOL_META[name]
        if i in revealed_idxs:
            state_cls = "done"
            badge_html = "<span class='badge good' style='font-size:10px;'>OK</span>"
            dot_inner = icon("check", 14, color="var(--good)")
        elif i == active_idx:
            state_cls = "active"
            badge_html = "<span class='badge brand' style='font-size:10px;'>Ejecutando…</span>"
            dot_inner = "<div class='pulse-dot'></div>"
        else:
            state_cls = "idle"
            badge_html = ""
            dot_inner = "<div class='small-dot'></div>"

        entry = idx_to_entry.get(i)
        out_html = ""
        chev_html = ""
        if state_cls != "idle":
            # native HTML <details> handles collapse/expand without Streamlit reruns
            chev_html = (
                f"<span style='margin-left:auto; color:var(--ink-4); flex-shrink:0;' title='Toggle output'>"
                f"{icon('chevron-down', 14)}</span>"
            )
        if state_cls == "done" and entry is not None:
            output = _entry_output(entry)
            if output is not None:
                try:
                    text = json.dumps(output, ensure_ascii=False, indent=2, default=str)
                except (TypeError, ValueError):
                    text = str(output)
                if len(text) > 400:
                    text = text[:400] + "\n…"
                out_html = (
                    f"<details style='margin-top:8px;'>"
                    f"<summary style='font-size:10px; text-transform:uppercase; letter-spacing:0.08em; "
                    f"color:var(--ink-3); cursor:pointer; list-style:none; padding-left:32px;'>"
                    f"Ver output</summary>"
                    f"<pre style='margin:6px 0 0 32px; padding:10px 12px; background:#0e1a2c; "
                    f"color:#cbe2ff; border-radius:8px; font-size:11px; font-family:var(--mono); "
                    f"line-height:1.5; max-height:140px; overflow:auto; white-space:pre-wrap; "
                    f"word-break:break-word;'>{html.escape(text)}</pre>"
                    f"</details>"
                )

        parts.append(
            f"<div class='tl-step {state_cls}'>"
            f"<div class='dot-wrap'><div class='dot'>{dot_inner}</div></div>"
            f"<div class='body'>"
            f"<div class='row1'>"
            f"<span class='ico-tool'>{icon(meta['icon'], 15)}</span>"
            f"<div style='flex:1; min-width:0;'>"
            f"<div class='meta-line'>"
            f"<span class='idx'>{i+1:02d}</span>"
            f"<span class='name'>{html.escape(meta['label'])}</span>"
            f"{badge_html}"
            f"</div>"
            f"<div class='source-line'>{html.escape(name)}() "
            f"<span class='source-tag'>· {html.escape(meta['source'])}</span></div>"
            f"</div>"
            f"{chev_html}"
            f"</div>"
            f"{out_html}"
            f"</div>"
            f"</div>"
        )

    parts.append("</div>")
    box.html(
        f"<div class='card'>"
        f"<div class='card-h'>"
        f"<span style='color: var(--brand);'>{icon('cpu', 16)}</span>"
        f"<h3>Trace del agente</h3>"
        f"<div class='meta num'>{len(revealed_idxs)}/{total_steps} pasos · {elapsed:.1f}s</div>"
        f"</div>"
        + "".join(parts) + "</div>"
    )


def _render_thinking(box: Any, *, transcript_lines: list[tuple[int, str]], active_idx: int) -> None:
    if not transcript_lines:
        body = (
            "<div class='transcript'><div class='line' style='color:#7e93b3; font-style:italic;'>"
            "Inicializando…</div></div>"
        )
    else:
        lines = []
        for idx, narr in transcript_lines:
            cls = "line active" if idx == active_idx else "line"
            cursor = "<span class='cursor'></span>" if idx == active_idx else ""
            lines.append(f"<div class='{cls}'><span class='gt'>›</span>{html.escape(narr)}{cursor}</div>")
        body = "<div class='transcript scroll-thin'>" + "".join(lines) + "</div>"

    box.html(
        f"""
        <div class='thinking'>
          <div class='head'>
            <div class='sq'>{icon('sparkle', 16, color='white')}</div>
            <div>
              <div class='title'>Claude Sonnet 4.6</div>
              <div class='sub'>Razonando con tool use directo</div>
            </div>
          </div>
          {body}
        </div>
        """
    )


def _render_telemetry(box: Any, *, tokens: int, elapsed: float, tools_done: int) -> None:
    box.html(
        f"""
        <div class='card'>
          <div class='card-h'>
            <span style='color: var(--ink-3);'>{icon('pulse', 16)}</span>
            <h3>Telemetría</h3>
          </div>
          <div class='card-b'>
            <div class='telem-grid'>
              <div class='telem'>
                <div class='label'>Tokens consumidos</div>
                <div class='value'>{tokens:,}</div>
              </div>
              <div class='telem'>
                <div class='label'>Tiempo</div>
                <div class='value'>{elapsed:.1f}<span class='suffix'>s</span></div>
              </div>
              <div class='telem'>
                <div class='label'>Tools llamadas</div>
                <div class='value'>{tools_done}<span class='suffix'>/{len(TOOL_ORDER)}</span></div>
              </div>
              <div class='telem'>
                <div class='label'>Iteraciones LLM</div>
                <div class='value'>{max(1, tools_done)}</div>
              </div>
            </div>
          </div>
        </div>
        """
    )


def _render_neuro_note(box: Any) -> None:
    box.html(
        f"""
        <div class='neuro-note'>
          <span class='ico'>{icon('shield', 18)}</span>
          <div class='body'>
            <b>Arquitectura neuro-simbólica</b>
            Claude orquesta y redacta. Las reglas críticas (carencia, exclusión,
            documentos) corren en Python determinístico — auditables, reproducibles.
          </div>
        </div>
        """
    )
