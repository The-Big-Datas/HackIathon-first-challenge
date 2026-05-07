"""Detalle screen — patient/policy/procedure/docs panels + agente listo card."""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

import api
import components
import state
import utils
from icons import icon


def render(informe_id: Optional[str]) -> None:
    if not informe_id:
        st.warning("No se ha seleccionado ningún informe.")
        if st.button("← Volver a la bandeja", key="detalle_back_noid"):
            state.go_to_bandeja()
        return

    detail: Optional[api.InformeDetail] = None
    slim: Optional[api.InformeListItem] = None
    detail_err: Optional[api.BackendError] = None
    try:
        detail = api.fetch_informe_detail(informe_id)
    except api.BackendError as err:
        detail_err = err

    if detail is None:
        try:
            informes = api.fetch_informes()
            slim = next((i for i in informes if i.id_informe == informe_id), None)
        except api.BackendError as err:
            components.error_panel(err, on_retry=lambda: st.rerun(), key_prefix="detalle_list")
            if st.button("← Volver a la bandeja", key="detalle_back_err"):
                state.go_to_bandeja()
            return

    if detail is None and slim is None:
        st.error(f"No se encontró el informe {informe_id} en el backend.")
        if st.button("← Volver a la bandeja", key="detalle_back_404"):
            state.go_to_bandeja()
        return

    descripcion = detail.descripcion_procedimiento if detail else (slim.descripcion_procedimiento if slim else "")

    # Page header — Volver button + h1 + procesar CTA on the same row
    head_cols = st.columns([1, 6, 2])
    with head_cols[0]:
        if st.button("← Volver", key="detalle_back", use_container_width=True):
            state.go_to_bandeja()
    with head_cols[1]:
        cpt_badge = (
            components.badge(detail.procedimiento_cpt, "neutral", mono=True)
            if detail and detail.procedimiento_cpt else ""
        )
        id_badge = components.badge(informe_id, "brand", mono=True)
        sub_text = ""
        if detail:
            parts = []
            if detail.hospital:
                parts.append(f"desde {html.escape(detail.hospital)}")
            if detail.medico_tratante:
                parts.append(f"enviado por {html.escape(detail.medico_tratante)}")
            sub_text = " · ".join(parts)
        elif slim:
            sub_text = f"desde {html.escape(slim.hospital or '—')}"
        st.html(
            f"""
            <div style='min-width:0;'>
              <div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>
                <h1 class='page-h1'>{html.escape(descripcion or 'Informe')}</h1>
                {cpt_badge}
                {id_badge}
              </div>
              <div class='page-sub' style='margin-top:6px;'>
                {sub_text or '—'}
              </div>
            </div>
            """
        )
    with head_cols[2]:
        st.html("<div style='height:8px;'></div>")
        if st.button(
            "✦ Procesar pre-autorización",
            key="detalle_procesar",
            type="primary",
            use_container_width=True,
        ):
            state.go_to_procesando(informe_id)

    if detail_err is not None and detail_err.kind != "http":
        st.html(
            f"<div style='color: var(--ink-3); font-size: 12px; padding: 8px 0;'>"
            f"Detalle limitado: {html.escape(str(detail_err))}</div>"
        )

    # 2-col grid: left = informe panels, right = agente listo + cobertura preview
    col_left, col_right = st.columns([16, 11], gap="medium")

    with col_left:
        if detail is not None:
            _render_left_full(detail)
        else:
            _render_left_slim(slim, informe_id)

    with col_right:
        _render_agent_ready(informe_id)
        _render_coverage_preview(detail)


def _render_left_full(d: api.InformeDetail) -> None:
    edad = utils.calc_edad(d.paciente_fecha_nacimiento)
    edad_sexo = (f"{edad} años · {d.paciente_sexo}".rstrip(" ·")
                 if edad is not None
                 else (d.paciente_sexo or "—"))
    plan_html = components.plan_badge(d.plan_nivel, d.plan_nombre) if d.plan_nivel or d.plan_nombre else "—"
    estado_html = (
        f"<span class='badge good'>● {html.escape(d.poliza_estado)}</span>"
        if d.poliza_estado == "Vigente"
        else (components.badge(d.poliza_estado, "warn") if d.poliza_estado else "—")
    )
    antig = ""
    if d.poliza_fecha_alta:
        try:
            from datetime import date, datetime
            alta = datetime.strptime(d.poliza_fecha_alta[:10], "%Y-%m-%d").date()
            antig = f"{(date.today() - alta).days} días"
        except Exception:
            antig = "—"

    asegurado_grid = components.kv_grid([
        components.kv_block("Paciente", html.escape(d.paciente_nombre or "—")),
        components.kv_block("Cédula", f"<span class='value mono'>{html.escape(d.paciente_cedula or '—')}</span>"),
        components.kv_block("Edad / Sexo", html.escape(edad_sexo)),
        components.kv_block("Póliza", f"<span class='value mono'>{html.escape(d.poliza_numero or '—')}</span>"),
        components.kv_block("Plan", plan_html),
        components.kv_block("Estado", estado_html),
        components.kv_block("Fecha de alta", html.escape(utils.fmt_date(d.poliza_fecha_alta))),
        components.kv_block("Antigüedad", html.escape(antig or "—")),
        components.kv_block("Nivel del plan", html.escape(d.plan_nivel or "—")),
    ])
    components.card_html(
        "Asegurado y póliza",
        asegurado_grid,
        icon_name="user",
        meta_html=f"{icon('database', 11)} Notion · Asegurados, Pólizas",
    )

    proc_grid = components.kv_grid([
        components.kv_block(
            "Diagnóstico (CIE-10)",
            f"<span class='value mono'>{html.escape(d.diagnostico_cie10 or '—')}</span>",
            sub_html=html.escape(d.diagnostico_desc or ""),
        ),
        components.kv_block(
            "Procedimiento (CPT)",
            f"<span class='value mono'>{html.escape(d.procedimiento_cpt or '—')}</span>",
            sub_html=html.escape(d.descripcion_procedimiento or ""),
        ),
        components.kv_block("Programada para", html.escape(utils.fmt_date(d.fecha_programada))),
    ])

    proc_inner = (
        f"{proc_grid}"
        f"<div style='border-top:1px solid var(--line); padding-top:14px; margin-top:14px;'>"
        f"<div class='eyebrow' style='margin-bottom:8px;'>Justificación clínica</div>"
        f"<p style='margin:0; font-size:13.5px; line-height:1.55; color:var(--ink-2);'>"
        f"{html.escape(d.justificacion_clinica or '—')}</p>"
        f"</div>"
        f"<div style='display:flex; gap:18px; font-size:12px; color:var(--ink-3); "
        f"border-top:1px solid var(--line); padding-top:14px; margin-top:14px; flex-wrap:wrap;'>"
        f"<span>{icon('hospital', 13)} {html.escape(d.hospital or '—')}</span>"
        f"<span>{icon('user', 13)} {html.escape(d.medico_tratante or '—')}</span>"
        f"<span>{icon('calendar', 13)} Emitido {html.escape(utils.fmt_date(d.fecha_emision))}</span>"
        f"</div>"
    )
    components.card_html(
        "Procedimiento solicitado",
        proc_inner,
        icon_name="pulse",
        meta_html="CIE-10 · CPT",
    )

    if d.documentos_adjuntos:
        chips = "<div class='doc-row'>" + "".join(
            components.doc_chip(utils.doc_label(c), present=True) for c in d.documentos_adjuntos
        ) + "</div>"
    else:
        chips = (
            "<div style='color:var(--ink-3); font-size:12.5px;'>"
            "Sin documentos adjuntos.</div>"
        )
    components.card_html(
        "Documentos adjuntos",
        chips,
        icon_name="doc",
        meta_html=f"{len(d.documentos_adjuntos)} archivo{'s' if len(d.documentos_adjuntos) != 1 else ''}",
    )


def _render_left_slim(slim: Optional[api.InformeListItem], informe_id: str) -> None:
    st.html(
        "<div style='font-size:12px; color:var(--ink-3); margin-bottom:8px;'>"
        "Vista resumida — el backend aún no expone "
        "<span class='mono'>GET /informes/{id}</span> para los detalles completos."
        "</div>"
    )
    rows = components.kv_grid([
        components.kv_block("Identificador", f"<span class='value mono'>{html.escape(informe_id)}</span>"),
        components.kv_block(
            "Procedimiento",
            html.escape((slim.descripcion_procedimiento if slim else None) or "—"),
        ),
        components.kv_block("Hospital", html.escape((slim.hospital if slim else None) or "—")),
    ])
    components.card_html("Informe", rows, icon_name="doc")


def _render_agent_ready(informe_id: str) -> None:
    steps_html = ""
    for i, txt in enumerate([
        "Lee informe en Notion",
        "Verifica vigencia y plan de la póliza",
        "Consulta cobertura del CPT",
        "Calcula carencia (determinístico)",
        "Valida documentos requeridos",
        "Emite decisión y la guarda en Notion",
    ], 1):
        steps_html += (
            f"<div class='step'>"
            f"<span class='num'>{i}</span>"
            f"<span>{html.escape(txt)}</span>"
            f"</div>"
        )

    st.html(
        f"""
        <div class='agent-ready'>
          <div class='head'>
            <div class='sq'>{icon('sparkle', 18, color='white')}</div>
            <div>
              <div class='title'>Agente listo</div>
              <div class='sub'>Claude Sonnet 4.6 · 6 herramientas disponibles</div>
            </div>
          </div>
          <div class='steps'>{steps_html}</div>
        </div>
        """
    )

    # Inline CTA right under the gradient card
    if st.button(
        "✦ Procesar pre-autorización",
        key="detalle_procesar_side",
        type="primary",
        use_container_width=True,
    ):
        state.go_to_procesando(informe_id)
    st.html(
        "<div style='font-size:11px; color:var(--ink-3); text-align:center; margin-top:6px;'>"
        "~5–8 segundos · trace completo registrado</div>"
    )


def _render_coverage_preview(detail: Optional[api.InformeDetail]) -> None:
    cob: Optional[api.Cobertura] = None
    if detail and detail.procedimiento_cpt and detail.plan_id:
        cob = api.fetch_cobertura(detail.procedimiento_cpt, detail.plan_id)

    if cob is None or not detail or not detail.procedimiento_cpt:
        body_html = (
            "<div style='font-size:13px; color:var(--ink-3);'>"
            "La regla de cobertura se carga al procesar el caso."
            "</div>"
        )
        components.card_html("Regla de cobertura aplicable", body_html, icon_name="shield")
        return

    if not cob.cubierto:
        body_html = (
            f"<div style='font-size:13px; color:var(--bad-ink);'>"
            f"No existe regla de cobertura para CPT {html.escape(detail.procedimiento_cpt)} bajo "
            f"{html.escape(detail.plan_nombre or detail.plan_nivel or '—')}."
            f"</div>"
        )
        components.card_html("Regla de cobertura aplicable", body_html, icon_name="shield")
        return

    docs_chips = "".join(
        f"<span class='tag-doc'>{html.escape(utils.doc_label(d))}</span>"
        for d in cob.documentos_requeridos
    )
    docs_section = docs_chips or "<span style='color:var(--ink-3); font-size:12px;'>Ninguno</span>"
    body_html = (
        f"<div style='display:flex; flex-direction:column; gap:12px;'>"
        f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
        f"<span style='font-size:12px; color:var(--ink-3);'>Cubierto bajo el plan</span>"
        f"<span class='badge good'>{icon('check', 11)} Sí</span>"
        f"</div>"
        f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
        f"<span style='font-size:12px; color:var(--ink-3);'>Carencia requerida</span>"
        f"<span class='num' style='font-weight:500; font-size:13px;'>{cob.dias_carencia} días</span>"
        f"</div>"
        f"<div>"
        f"<div style='font-size:12px; color:var(--ink-3); margin-bottom:6px;'>Documentos requeridos</div>"
        f"<div style='display:flex; flex-wrap:wrap; gap:6px;'>{docs_section}</div>"
        f"</div>"
        f"</div>"
    )
    components.card_html("Regla de cobertura aplicable", body_html, icon_name="shield")
