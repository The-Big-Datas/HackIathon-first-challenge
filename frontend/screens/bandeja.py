"""Bandeja screen — single-card table where each row is one clickable element.

Click handling uses a query-param link pattern: each row is wrapped in
``<a href="?open=ID">``. At the top of ``render()`` we read the query
param, validate it against the informe-id allowlist, clear it, and route
to the detalle stage. This keeps the entire row as one visual unit while
the validation gate prevents path-traversal/oversize/unicode attacks
through the URL.

Per-row detail enrichment is parallelized via ThreadPoolExecutor and
cached for 60s with ``st.cache_data`` so reruns don't re-fetch.
"""

from __future__ import annotations

import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import streamlit as st

import api
import components
import state
from icons import icon


@st.cache_data(ttl=60, show_spinner=False)
def _cached_fetch_informes() -> list[api.InformeListItem]:
    """fetch_informes wrapped in a 60s cache to absorb Streamlit reruns."""
    return api.fetch_informes()


@st.cache_data(ttl=60, show_spinner=False)
def _cached_fetch_detail(informe_id: str) -> Optional[api.InformeDetail]:
    """fetch_informe_detail wrapped in a 60s cache."""
    return api.fetch_informe_detail(informe_id)


def _fetch_details_parallel(
    informes: list[api.InformeListItem],
) -> dict[str, Optional[api.InformeDetail]]:
    """Fetch detail for each informe in parallel (max 4 workers).

    Per-row failures degrade to None — tracked in the returned dict so the
    caller can render an inline error chip instead of a silent em-dash.
    """
    out: dict[str, Optional[api.InformeDetail]] = {}
    if not informes:
        return out
    with ThreadPoolExecutor(max_workers=min(4, len(informes))) as pool:
        future_to_id = {
            pool.submit(_cached_fetch_detail, inf.id_informe): inf.id_informe
            for inf in informes
        }
        for fut in as_completed(future_to_id):
            informe_id = future_to_id[fut]
            try:
                out[informe_id] = fut.result()
            except api.BackendError:
                out[informe_id] = None
    return out


def render() -> None:
    # Whole-row click handler. The link sets ?open=<id>; we read it on the
    # next rerun, validate against the allowlist, clear it, and navigate.
    qp = st.query_params
    if "open" in qp:
        target = qp.get("open") or ""
        del st.query_params["open"]
        if state.is_valid_informe_id(target):
            state.go_to_detalle(target)
            return  # state.go_to_detalle calls st.rerun(); not reached.
        # Invalid id: drop silently. The user-visible result is just a no-op
        # navigation; no error_panel because this is most likely a stale link
        # rather than user-actionable.

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
        informes = _cached_fetch_informes()
    except api.BackendError as err:
        components.error_panel(
            err,
            on_retry=lambda: (_cached_fetch_informes.clear(), st.rerun()),
            key_prefix="bandeja",
        )
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
    details = _fetch_details_parallel(informes)

    processed_ids = st.session_state.processed_ids
    pending = [i for i in informes if i.id_informe not in processed_ids]

    # Per-id decision counts — replaces the old "single last_result drives all
    # rows" bug where INF-001=Aprobado then INF-002=Negado made BOTH rows show
    # Negado.
    counts = state.decision_counts(
        st.session_state.results_by_id or {},
        [i.id_informe for i in informes],
    )

    components.stat_grid([
        components.stat_tile("Pendientes", len(pending), tone="brand", ico="inbox"),
        components.stat_tile("Aprobados hoy", counts["Aprobado"], tone="good", ico="check-circle"),
        components.stat_tile("Negados hoy", counts["Negado"], tone="bad", ico="x-circle"),
        components.stat_tile("Pidiendo docs", counts["Documentos_Faltantes"], tone="warn", ico="alert"),
    ])

    # Build all rows as one HTML string so the entire table emits in a
    # single st.html call — which keeps it inside one card visually.
    rows_html = ""
    detail_failed_ids: list[str] = []
    for inf in informes:
        d = details.get(inf.id_informe)
        if d is None and inf.id_informe in details:
            # detail fetch failed for this row (vs. just not-yet-fetched)
            detail_failed_ids.append(inf.id_informe)

        is_done = inf.id_informe in processed_ids
        # Per-id status: look up the actual decision for this informe instead
        # of the single global last_result.
        result = state.get_result_for(inf.id_informe)
        if is_done and result is not None and result.decision is not None:
            status_text = result.decision.decision
        elif is_done:
            status_text = "procesado"
        else:
            status_text = "pendiente"
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

    if detail_failed_ids:
        st.html(
            f"""
            <div style='margin-top:10px; padding:8px 14px; background:var(--warn-bg);
                        color:var(--warn-ink); border:1px solid rgba(176,114,6,.25);
                        border-radius:8px; font-size:12px;'>
              No se pudieron cargar los detalles de
              <span class='mono'>{', '.join(html.escape(i) for i in detail_failed_ids)}</span>.
              Verifica que el backend esté disponible.
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
