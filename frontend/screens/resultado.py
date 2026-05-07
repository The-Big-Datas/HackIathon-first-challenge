"""Resultado screen — verdict hero + checks + agent message + registro side."""

from __future__ import annotations

import html
from typing import Any, Optional

import streamlit as st

import api
import components
import state
import utils
from icons import icon

# Reuse tool meta from procesando for trace mini
from screens.procesando import TOOL_META


def render(result: Optional[api.ProcesarResponse]) -> None:
    if result is None:
        st.warning("No hay resultado disponible. Vuelve a la bandeja para procesar un informe.")
        if st.button("← Volver a la bandeja", key="res_back_empty"):
            state.go_to_bandeja()
        return

    decision = result.decision
    decision_label = decision.decision if decision else "Sin decisión"
    tone = utils.decision_tone(decision.decision if decision else None)

    # Top action row — left: Volver, Bandeja; right: Re-procesar, Copiar resumen, Exportar
    top = st.columns([1.4, 1, 3, 1.4, 1.6, 1.4])
    with top[0]:
        if st.button("← Volver al informe", key="res_back_top", use_container_width=True):
            state.go_to_detalle(st.session_state.selected_informe_id)
    with top[1]:
        if st.button("⚐ Bandeja", key="res_inbox", use_container_width=True):
            state.go_to_bandeja()
    with top[3]:
        if st.button("▷ Re-procesar", key="res_reprocesar", use_container_width=True):
            state.go_to_procesando(st.session_state.selected_informe_id)
    with top[4]:
        st.button("⌘ Copiar resumen", key="res_copy", use_container_width=True, disabled=True)
    with top[5]:
        st.button("↓ Exportar PDF", key="res_export", use_container_width=True, disabled=True)

    col_left, col_right = st.columns([16, 11], gap="medium")
    with col_left:
        _render_hero(decision, decision_label, tone, result)
        _render_checks(result)
        _render_agent_message(decision_label)

    with col_right:
        _render_registro(decision, result.trace)
        _render_trace_summary(result.trace)
        _render_notificar()


def _render_hero(
    decision: Optional[api.Decision],
    decision_label: str,
    tone: str,
    result: api.ProcesarResponse,
) -> None:
    palette_emblem = {"good": "check-circle", "bad": "x-circle", "warn": "alert"}.get(tone, "alert")
    palette_label = {
        "Aprobado": ("APPROVED", "Aprobado"),
        "Negado": ("DENIED", "Negado"),
        "Documentos_Faltantes": ("PENDING DOCS", "Documentos faltantes"),
    }.get(decision_label, ("DECISION", decision_label))
    eyebrow_tag, big_label = palette_label

    justificacion = decision.justificacion if decision else (result.final_text or "")
    docs_falt_html = ""
    if decision and decision.documentos_faltantes:
        chips = "".join(
            f"<span style='padding:6px 10px; background:#fff; "
            f"border:1px solid rgba(176,114,6,.4); border-radius:7px; "
            f"font-size:12.5px; color:var(--warn-ink); display:inline-flex; "
            f"align-items:center; gap:6px;'>"
            f"{icon('doc', 13)}{html.escape(utils.doc_label(d))}</span>"
            for d in decision.documentos_faltantes
        )
        docs_falt_html = (
            f"<div style='margin-top:14px;'>"
            f"<div class='eyebrow' style='margin-bottom:8px;'>Documentos faltantes</div>"
            f"<div style='display:flex; flex-wrap:wrap; gap:8px;'>{chips}</div>"
            f"</div>"
        )

    clausula_html = ""
    if decision and decision.clausula_aplicada:
        # Try to find decision_id from the trace's emitir_decision output
        decision_id = ""
        for entry in result.trace:
            tool = entry.tool if hasattr(entry, "tool") else (entry.get("tool") if isinstance(entry, dict) else "")
            if tool == "emitir_decision":
                output = entry.output if hasattr(entry, "output") else (entry.get("output") if isinstance(entry, dict) else None)
                if isinstance(output, dict):
                    decision_id = output.get("decision_id", "")
                break
        clausula_html = (
            f"<div class='clausula'>"
            f"<span>{icon('shield', 12)} {html.escape(decision.clausula_aplicada)}</span>"
            f"<span class='sep'>·</span>"
            f"<span class='mono'>{html.escape(decision_id or '—')}</span>"
            f"</div>"
        )

    # Build a descriptive summary line: "Descripción · CPT · Paciente".
    # Pull what we can from the get_informe_medico trace + the cached
    # InformeDetail (if available) — the agent's output usually has cpt
    # and cedula; nombre + descripcion need a fresh detail fetch.
    cpt = ""
    cedula = ""
    for entry in result.trace:
        tool = entry.tool if hasattr(entry, "tool") else (entry.get("tool") if isinstance(entry, dict) else "")
        if tool == "get_informe_medico":
            output = entry.output if hasattr(entry, "output") else (entry.get("output") if isinstance(entry, dict) else None)
            if isinstance(output, dict):
                cpt = output.get("procedimiento_cpt", "") or ""
                cedula = output.get("paciente_cedula", "") or ""
            break

    detail = None
    informe_id = st.session_state.get("selected_informe_id")
    if informe_id:
        try:
            detail = api.fetch_informe_detail(informe_id)
        except api.BackendError:
            detail = None

    summary_parts: list[str] = []
    if detail and detail.descripcion_procedimiento:
        summary_parts.append(html.escape(detail.descripcion_procedimiento))
    if cpt:
        summary_parts.append(f"<span class='mono'>{html.escape(cpt)}</span>")
    if detail and detail.paciente_nombre:
        summary_parts.append(html.escape(detail.paciente_nombre))
    elif cedula:
        summary_parts.append(f"<span class='mono'>{html.escape(cedula)}</span>")
    procedure_summary = " · ".join(summary_parts) if summary_parts else ""

    st.html(
        f"""
        <div class='verdict-hero {tone}'>
          <div class='corner-circle'></div>
          <div class='row'>
            <div class='emblem'>{icon(palette_emblem, 28, color='white')}</div>
            <div>
              <div class='eyebrow'>DECISIÓN · {eyebrow_tag}</div>
              <div class='label-big'>{html.escape(big_label)}</div>
              <div class='summary'>{procedure_summary}</div>
            </div>
          </div>

          <div class='glass'>
            <div class='label'>Justificación</div>
            <p>{html.escape(justificacion or '—')}</p>
          </div>

          {docs_falt_html}
          {clausula_html}
        </div>
        """
    )


def _render_checks(result: api.ProcesarResponse) -> None:
    """Build the check-row list dynamically from whatever the trace contains."""
    def _get(tool: str) -> Optional[Any]:
        for e in result.trace:
            t = e.tool if hasattr(e, "tool") else (e.get("tool") if isinstance(e, dict) else "")
            if t == tool:
                return e
        return None

    def _out(entry: Any) -> dict:
        if entry is None:
            return {}
        o = entry.output if hasattr(entry, "output") else (entry.get("output") if isinstance(entry, dict) else None)
        return o if isinstance(o, dict) else {}

    poliza = _get("get_poliza_paciente")
    cob = _get("get_cobertura")
    car = _get("verificar_carencia")
    docs = _get("validar_documentos")

    rows: list[dict[str, Any]] = []
    if poliza:
        po = _out(poliza)
        rows.append({
            "label": "Vigencia de la póliza",
            "detail": f"{po.get('numero', '—')} · {po.get('estado', '—')}",
            "ok": po.get("estado") == "Vigente",
        })
    if cob:
        co = _out(cob)
        cubierto = co.get("cubierto") is not False
        rows.append({
            "label": "Cobertura del procedimiento",
            "detail": "Cubierto bajo el plan" if cubierto else "No cubierto bajo el plan",
            "ok": cubierto,
        })
    if car:
        ca = _out(car)
        rows.append({
            "label": "Período de carencia",
            "detail": (
                f"{ca.get('dias_transcurridos', 0)} días transcurridos / "
                f"{ca.get('dias_requeridos', 0)} requeridos"
            ),
            "ok": ca.get("cumple") is True,
            "extra": (
                f"Faltan {ca.get('dias_faltantes', 0)} días"
                if ca.get("cumple") is False else None
            ),
        })
    elif cob and _out(cob).get("cubierto") is False:
        rows.append({"label": "Período de carencia", "detail": "No evaluado — cobertura excluida", "ok": None})

    if docs:
        do = _out(docs)
        falt = do.get("documentos_faltantes") or []
        ok = do.get("completo") is True
        rows.append({
            "label": "Documentos requeridos",
            "detail": "Completos" if ok else f"Faltan {len(falt)} documento{'s' if len(falt) != 1 else ''}",
            "ok": ok,
        })
    else:
        rows.append({"label": "Documentos requeridos", "detail": "No evaluado", "ok": None})

    rows_html = ""
    for r in rows:
        ok = r["ok"]
        cls = "ok" if ok is True else ("bad" if ok is False else "na")
        ico_name = "check" if ok is True else ("x" if ok is False else "clock")
        extra = f" · {html.escape(r.get('extra', ''))}" if r.get("extra") else ""
        rows_html += (
            f"<div class='check-row {cls}'>"
            f"<div class='ico-sq'>{icon(ico_name, 13)}</div>"
            f"<div class='body'>"
            f"<div class='label'>{html.escape(r['label'])}</div>"
            f"<div class='detail'>{html.escape(r['detail'])}{extra}</div>"
            f"</div>"
            f"</div>"
        )

    components.card_html(
        "Checks aplicados",
        rows_html,
        icon_name="check-shield",
        meta_html="policy engine · python",
    )


def _render_agent_message(decision_label: str) -> None:
    text = {
        "Aprobado": "Pre-autorización aprobada. La póliza está vigente, cumple la carencia "
                   "y todos los documentos requeridos están adjuntos. El paciente puede "
                   "proceder con la cirugía en la fecha programada.",
        "Negado": "Pre-autorización negada. He registrado la decisión en Notion con la "
                  "justificación detallada y la cláusula aplicable, para que el equipo de "
                  "servicio al cliente pueda comunicarse con el paciente.",
        "Documentos_Faltantes": "Pre-autorización en pausa. Faltan documentos críticos para "
                                "completar la evaluación. Una vez recibidos, reenvíe el caso "
                                "y el agente lo procesará nuevamente.",
    }.get(decision_label, "—")

    components.card_html(
        "Mensaje del agente",
        f"<div style='font-size:13.5px; line-height:1.6; color:var(--ink-2); font-style:italic;'>"
        f"\"{html.escape(text)}\"</div>",
        icon_name="sparkle",
        meta_html="Claude Sonnet 4.6",
    )


def _render_registro(decision: Optional[api.Decision], trace: list[Any]) -> None:
    decision_id = _decision_id_from_trace(trace)
    from datetime import datetime
    timestamp = datetime.now().strftime("%d %b %Y · %H:%M:%S")

    components.card_html(
        "Registro",
        f"""
        <div class='reg-row'><span class='k'>ID Decisión</span>
          <span class='v mono'>{html.escape(decision_id or '—')}</span></div>
        <div class='reg-row'><span class='k'>Persistido en</span>
          <span class='v'>Notion · Decisiones</span></div>
        <div class='reg-row'><span class='k'>Timestamp</span>
          <span class='v num'>{html.escape(timestamp)}</span></div>
        <div class='reg-row'><span class='k'>Operador</span>
          <span class='v'>Agente automático</span></div>
        <div class='reg-row'><span class='k'>Modelo</span>
          <span class='v mono'>claude-sonnet-4-6</span></div>
        """,
        icon_name="archive",
    )


def _decision_id_from_trace(trace: list[Any]) -> str:
    for entry in trace:
        tool = entry.tool if hasattr(entry, "tool") else (entry.get("tool") if isinstance(entry, dict) else "")
        if tool == "emitir_decision":
            output = entry.output if hasattr(entry, "output") else (entry.get("output") if isinstance(entry, dict) else None)
            if isinstance(output, dict):
                return output.get("decision_id", "") or ""
    return ""


def _render_notificar() -> None:
    cols = st.columns([6, 2])
    with cols[0]:
        st.html(
            f"""
            <div class='card' style='background: linear-gradient(165deg, var(--brand-bg), #fff);
                                      border-color: rgba(23,99,209,.18);'>
              <div class='card-b' style='display:flex; gap:12px; align-items:center;'>
                <div style='width:36px; height:36px; border-radius:9px; background:#fff;
                            display:grid; place-items:center; color:var(--brand);
                            box-shadow:0 1px 3px rgba(0,0,0,.08); flex-shrink:0;'>
                  {icon('bell', 17)}
                </div>
                <div style='flex:1; min-width:0;'>
                  <div style='font-weight:600; font-size:13px;'>Notificar al paciente</div>
                  <div style='font-size:12px; color:var(--ink-3);'>Email + SMS con la decisión y próximos pasos.</div>
                </div>
              </div>
            </div>
            """
        )
    with cols[1]:
        st.html("<div style='height:18px;'></div>")
        st.button("Enviar", key="res_notify", type="primary", use_container_width=True, disabled=True)


def _render_trace_summary(trace: list[Any]) -> None:
    rows_html = ""
    for i, entry in enumerate(trace):
        tool = entry.tool if hasattr(entry, "tool") else (entry.get("tool") if isinstance(entry, dict) else "")
        meta = TOOL_META.get(tool, {"icon": "tool", "label": tool})
        rows_html += (
            f"<div class='trace-mini'>"
            f"<span class='idx'>{i+1:02d}</span>"
            f"<span class='ico'>{icon(meta['icon'], 13)}</span>"
            f"<span class='label'>{html.escape(meta['label'])}</span>"
            f"<span class='check'>{icon('check', 12)}</span>"
            f"</div>"
        )

    components.card_html_no_padding(
        "Resumen del trace",
        f"<div style='padding:8px 14px 14px 14px;'>{rows_html}</div>",
        icon_name="cpu",
        meta_html=f"{len(trace)} pasos",
    )

    # Full-trace expander for inspectors who want the raw payload
    with st.expander("Trace completo del agente"):
        for i, entry in enumerate(trace, 1):
            tool = entry.tool if hasattr(entry, "tool") else (entry.get("tool") if isinstance(entry, dict) else "")
            inp = entry.input if hasattr(entry, "input") else (entry.get("input", {}) if isinstance(entry, dict) else {})
            out = entry.output if hasattr(entry, "output") else (entry.get("output") if isinstance(entry, dict) else None)
            st.markdown(
                f"<div style='font-family:var(--mono); font-size:12px; font-weight:500; "
                f"color:var(--brand-ink); margin:8px 0 4px;'>#{i} · {html.escape(tool)}</div>",
                unsafe_allow_html=True,
            )
            ci, co = st.columns(2)
            with ci:
                st.markdown("<div style='font-size:11px; color:var(--ink-3);'>Input</div>", unsafe_allow_html=True)
                st.json(inp or {}, expanded=False)
            with co:
                st.markdown("<div style='font-size:11px; color:var(--ink-3);'>Output</div>", unsafe_allow_html=True)
                st.json(out or {}, expanded=False)
