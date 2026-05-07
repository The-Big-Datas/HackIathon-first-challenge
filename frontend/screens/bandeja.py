"""Bandeja screen — single-card table where each row is one clickable element.

Click handling uses a query-param link pattern: each row is wrapped in
``<a href="?open=ID">``. At the top of ``render()`` we read the query
param, clear it, and route to the detalle stage. This keeps the entire
row as one visual unit (matching the React mockup) without needing a
separate Streamlit button per row.
"""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

import api
import components
import state
from icons import icon


def render() -> None:
    # Whole-row click handler. The link sets ?open=<id>; we read it on the
    # next rerun, clear it, and navigate. Streamlit preserves session state
    # across same-origin query param changes, so processed_ids and last_result
    # survive the click.
    qp = st.query_params
    if "open" in qp:
        target = qp.get("open") or ""
        if target:
            del st.query_params["open"]
            state.go_to_detalle(target)
            return  # state.go_to_detalle calls st.rerun(); not reached.

    trailing = (
        f"<button class='hdr-btn' type='button'>{icon('filter', 14)}<span>Filtrar</span></button>"
        f"<button class='hdr-btn' type='button'>{icon('download', 14)}<span>Exportar</span></button>"
    )
    components.page_header(
        "Bandeja de pre-autorización",
        "Informes médicos pendientes de revisión por el agente.",
        trailing_html=trailing,
    )

    try:
        informes = api.fetch_informes()
    except api.BackendError as err:
        components.error_panel(err, on_retry=lambda: st.rerun(), key_prefix="bandeja")
        return

    if not informes:
        st.html(
            """
            <div class='card'>
              <div class='card-b' style='text-align:center; padding:40px;'>
                <div style='font-size:32px; margin-bottom:8px;'>📭</div>
                <div style='font-weight:500; color:var(--ink); font-size:14px;'>
                  No hay informes en Notion
                </div>
                <div style='color:var(--ink-3); font-size:12px; margin-top:6px;'>
                  Corre el script de seed para poblar las 3 demos
                  (<span class='mono'>python seed/populate_notion.py</span>).
                </div>
              </div>
            </div>
            """
        )
        return

    informes = sorted(informes, key=lambda i: i.id_informe)

    details: dict[str, Optional[api.InformeDetail]] = {}
    for inf in informes:
        try:
            details[inf.id_informe] = api.fetch_informe_detail(inf.id_informe)
        except api.BackendError:
            details[inf.id_informe] = None

    processed_ids = st.session_state.processed_ids
    pending = [i for i in informes if i.id_informe not in processed_ids]

    last = st.session_state.last_result
    aprobados = 0
    negados = 0
    docs_falt = 0
    if last and last.decision:
        if last.decision.decision == "Aprobado":
            aprobados = 1
        elif last.decision.decision == "Negado":
            negados = 1
        elif last.decision.decision == "Documentos_Faltantes":
            docs_falt = 1

    components.stat_grid([
        components.stat_tile("Pendientes", len(pending), tone="brand", ico="inbox"),
        components.stat_tile("Aprobados hoy", aprobados, tone="good", ico="check-circle"),
        components.stat_tile("Negados hoy", negados, tone="bad", ico="x-circle"),
        components.stat_tile("Pidiendo docs", docs_falt, tone="warn", ico="alert"),
    ])

    # Build all rows as one HTML string so the entire table emits in a
    # single st.html call — which keeps it inside one card visually.
    rows_html = ""
    for inf in informes:
        d = details.get(inf.id_informe)
        is_done = inf.id_informe in processed_ids
        status_text = "pendiente"
        if is_done and last and last.decision:
            status_text = last.decision.decision
        chip = components.status_chip(status_text)

        if d:
            paciente = d.paciente_nombre or "—"
            cpt = d.procedimiento_cpt or "—"
            descripcion = d.descripcion_procedimiento or inf.descripcion_procedimiento or "—"
            hospital = d.hospital or inf.hospital or "—"
            medico = d.medico_tratante or "—"
            plan_html = (
                components.plan_badge(d.plan_nivel, d.plan_nivel)
                if d.plan_nivel else components.badge("—", "neutral")
            )
            urgencia_html = components.urgency_chip(d.urgencia or "Electiva")
        else:
            paciente = "—"
            cpt = "—"
            descripcion = inf.descripcion_procedimiento or "—"
            hospital = inf.hospital or "—"
            medico = "—"
            plan_html = components.badge("—", "neutral")
            urgencia_html = components.urgency_chip("Electiva")

        rows_html += (
            f"<a class='inbox-row-link' href='?open={html.escape(inf.id_informe)}' target='_self'>"
            f"<div class='inbox-row'>"
            f"<div class='id'>{html.escape(inf.id_informe)}</div>"
            f"<div>"
            f"  <div class='primary'>{html.escape(paciente)}</div>"
            f"  <div class='sub'><span class='mono'>{html.escape(cpt)}</span>"
            f"  <span class='dot-sep'>·</span>{html.escape(descripcion)}</div>"
            f"</div>"
            f"<div>"
            f"  <div style='font-size:13px; color:var(--ink);'>{html.escape(hospital)}</div>"
            f"  <div class='sub'>{html.escape(medico)}</div>"
            f"</div>"
            f"<div>{plan_html}</div>"
            f"<div>{urgencia_html}</div>"
            f"<div>{chip}</div>"
            f"<div class='chev'>{icon('chevron-right', 16)}</div>"
            f"</div>"
            f"</a>"
        )

    st.html(
        f"""
        <div class='card'>
          <div class='card-h'>
            <span style='color: var(--ink-3);'>{icon('inbox', 16)}</span>
            <h3>Cola de informes</h3>
            <div class='meta'>
              <span class='badge neutral num'>{len(informes)}</span>
              <span style='margin-left:8px;'>Source · Notion {icon('link', 11)}</span>
            </div>
          </div>
          <div class='inbox-head'>
            <div>Informe</div>
            <div>Paciente · CPT</div>
            <div>Hospital · Médico</div>
            <div>Plan</div>
            <div>Urgencia</div>
            <div>Estado</div>
            <div></div>
          </div>
          {rows_html}
        </div>
        """
    )

    st.html(
        f"""
        <div style='margin-top:14px; display:flex; gap:10px; align-items:center;
                    color:var(--ink-3); font-size:12px;'>
          {icon('sparkle', 14)}
          <span>Powered by Claude Sonnet 4.6 · razonamiento neuro-simbólico con tool use directo</span>
        </div>
        """
    )
