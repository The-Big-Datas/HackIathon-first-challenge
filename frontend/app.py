"""Streamlit entry point for the Pre-Autorización Quirúrgica frontend.

Run locally:
    cd frontend && streamlit run app.py

Deploy:
    Streamlit Community Cloud, with BACKEND_URL set in .streamlit/secrets.toml.
"""

from __future__ import annotations

import streamlit as st

import components
import state
import styles
from screens import bandeja, detalle, procesando, resultado

st.set_page_config(
    page_title="Pre-Autorización Quirúrgica · hackIAthon",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

state.init_session()
styles.inject()

stage = st.session_state.stage
informe_id = st.session_state.selected_informe_id

# Sidebar (dark navy nav)
components.render_sidebar(stage, total_informes=3)

# Topbar (breadcrumb + live pill)
breadcrumb: list[tuple[str, bool]] = [("Operación", False), ("Bandeja", False)]
if stage in ("detalle", "procesando", "resultado") and informe_id:
    breadcrumb.append((informe_id, True))
    if stage == "procesando":
        breadcrumb.append(("Procesando", False))
    elif stage == "resultado":
        breadcrumb.append(("Resultado", False))

components.topbar(breadcrumb=breadcrumb)

# Stage routing
if stage == "bandeja":
    bandeja.render()
elif stage == "detalle":
    detalle.render(informe_id)
elif stage == "procesando":
    procesando.render(informe_id)
elif stage == "resultado":
    resultado.render(st.session_state.last_result)
else:
    st.error(f"Estado desconocido: {stage}")
