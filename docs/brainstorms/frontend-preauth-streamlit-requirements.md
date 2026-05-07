---
date: 2026-05-07
topic: frontend-preauth-streamlit
---

# Pre-Autorización Quirúrgica · Streamlit Frontend

## Summary

A pure-Streamlit (Python) frontend that recreates the design's 4-screen flow — Bandeja → Detalle → Procesando → Resultado — wired to the FastAPI backend via the guide spec contract. The animated trace is preserved through a faux-streamed reveal that fills in placeholder steps once the response lands. Replaces the existing React/Babel `frontend/index.html` prototype.

---

## Problem Frame

The hackIAthon Reto 1 submission is judged on a 30–60 second click-through. The team currently has two disconnected artifacts: a polished 4-screen React/Babel prototype (`frontend/index.html`) that mocks all data client-side, and a stock single-page Streamlit example from the guide that talks to a real backend but looks generic. Neither is shippable on its own — the React file has no real backend connection, and the stock Streamlit loses the visual moments (animated trace, verdict hero, deterministic-checks breakdown) that make the agent's reasoning legible to a non-technical judge.

The guide also mandates a Python-only stack deployable to Streamlit Community Cloud. A dual-deploy (FastAPI + a separate React frontend) was considered and rejected in the guide's "fallback monolítico" section as too costly relative to the time budget. Compounding this, an earlier implementation pass dropped the React file into `frontend/` without going through brainstorm → plan → work → review, which is why we are restarting from scope.

---

## Actors

- A1. **Hackathon judge** — clicks through the deployed Streamlit URL on a phone or laptop, picks one of three demo informes, watches the agent process, reads the verdict. Has under a minute of attention.
- A2. **Frontend (Streamlit app)** — owns navigation, renders all 4 screens, calls the FastAPI backend, drives the faux-streamed trace reveal.
- A3. **FastAPI backend (teammate's track)** — exposes `GET /informes` and `POST /procesar/{informe_id}`. Source of truth for informe list and agent decisions.

---

## Key Flows

- F1. **Inspect and process an informe**
  - **Trigger:** Judge opens the deployed app
  - **Actors:** A1, A2, A3
  - **Steps:**
    1. App loads, fetches informe list from backend, renders Bandeja with 3 informes and stat tiles
    2. Judge clicks a row → Detalle screen shows patient/policy/procedure/docs panels and the 6 tool steps the agent will execute
    3. Judge clicks "Procesar pre-autorización" → Procesando screen renders with placeholders for the 6 tool steps
    4. Frontend POSTs to `/procesar/{informe_id}`, waits for response (5–15s)
    5. On response, frontend reveals each trace step sequentially with small delays, lighting up tool placeholders
    6. Frontend transitions to Resultado screen with verdict hero, justification, deterministic-checks breakdown, full trace expander
  - **Outcome:** Judge sees a verdict (Aprobado / Negado / Documentos faltantes) with traceable reasoning
  - **Covered by:** R1, R2, R3, R5, R6, R7, R8, R9, R10

- F2. **Backend unavailable**
  - **Trigger:** Judge opens app while backend is asleep, down, or unreachable
  - **Actors:** A1, A2, A3
  - **Steps:**
    1. App attempts `GET /informes`, request fails or times out
    2. Frontend shows a clear error message with the backend URL and a retry affordance
    3. Judge clicks retry → request retries
  - **Outcome:** Judge knows the failure is infrastructure, not the demo logic
  - **Covered by:** R12

---

## Requirements

**Navigation and routing**
- R1. The app is a single Streamlit page with stage-based routing via `st.session_state`. Stages: `bandeja` (default), `detalle`, `procesando`, `resultado`.
- R2. Stage transitions are explicit user actions or programmatic transitions tied to backend response. Back navigation from any stage returns to Bandeja.

**Bandeja screen**
- R3. Bandeja fetches the informe list from `GET /informes` on first render and displays each informe as a row showing `id_informe`, `descripcion_procedimiento`, and `hospital`.
- R4. Bandeja shows three stat tiles at top: total informes, processed, pending. "Processed" is tracked client-side per session — once the user has seen Resultado for an informe, it counts as processed in this session.

**Detalle screen**
- R5. Detalle shows four panels for the selected informe: patient (cédula, nombre, edad), policy (número, plan, fecha de alta, estado), procedure (CPT, descripción, fecha programada, urgencia, justificación clínica), documents (adjuntos with friendly labels). Edad is derived client-side from `fecha_nacimiento`; `sexo` is omitted from the layout because it is not in the backend data model.
- R6. Detalle shows a "Agente listo" card listing the 6 tool steps the agent will call: `get_informe_medico`, `get_poliza_paciente`, `get_cobertura`, `verificar_carencia`, `validar_documentos`, `emitir_decision`.
- R7. Detalle has a primary "Procesar pre-autorización" button that transitions to Procesando.

**Procesando screen and trace animation**
- R8. Procesando renders the 6 tool steps as placeholder cards in a vertical timeline before the backend call begins.
- R9. The frontend POSTs to `/procesar/{informe_id}` once Procesando renders. While the request is in flight, the active step shows a pulsing/animated state.
- R10. When the response lands, the frontend reveals each actual trace entry one-by-one with a small delay (~250ms each) using `st.empty()` placeholders. Each revealed step shows tool name, input, output, and a status indicator (ok / error). Steps not present in the trace stay greyed.
- R11. Procesando displays elapsed time and trace step count as live counters during the call.

**Error handling**
- R12. If `GET /informes` or `POST /procesar/{informe_id}` fails (non-2xx, timeout, network error), the affected screen shows a clear error message with the backend URL visible and a retry button. Backend timeouts use a 120-second client timeout to match the guide.

**Resultado screen**
- R13. Resultado shows a verdict hero scaled by decision: green for Aprobado, red for Negado, amber for Documentos_Faltantes.
- R14. Resultado shows the agent's justificación, cláusula aplicada, decision ID, and (when applicable) the list of documentos faltantes with friendly labels.
- R15. Resultado shows a deterministic-checks breakdown summarizing carencia (días transcurridos vs requeridos) and documents (required vs attached) when those tools were called.
- R16. Resultado includes an expander that shows the full agent trace (all tool calls with inputs and outputs).
- R17. Resultado has a "Volver a la bandeja" action that returns to R1's Bandeja state with the just-processed informe marked as processed for the session.

**Visual identity**
- R18. The app uses the design's color palette (clinical blue brand, semantic good/warn/bad), typography (Inter Tight + JetBrains Mono + Instrument Serif via Google Fonts), spacing, and component shapes — applied via `st.markdown` with a single injected `<style>` block.
- R19. Layout is desktop-first; the app is usable on mobile but is not redesigned for it.

**Backend integration**
- R20. The frontend reads `BACKEND_URL` from `st.secrets["BACKEND_URL"]` with `os.getenv("BACKEND_URL", "http://localhost:8000")` as fallback.
- R21. The frontend codes against the guide-spec contract: `GET /informes` returns a list of `{id_informe, descripcion_procedimiento, hospital}` and `POST /procesar/{informe_id}` returns `{trace: [{tool, input, output}], final_text, decision: {decision, justificacion, clausula_aplicada, documentos_faltantes}}`.

---

## Acceptance Examples

- AE1. **Covers R3, R12.** Given the backend is unreachable, when the user opens the app, they see a clear error message naming the backend URL and a retry button — not a blank screen and not a Streamlit traceback.
- AE2. **Covers R8, R9, R10.** Given the user clicks "Procesar pre-autorización" on INF-001, when the backend returns 6 trace entries, all 6 placeholder cards transition to the revealed state in sequence with their actual tool inputs/outputs visible.
- AE3. **Covers R10, R13.** Given INF-002 (carencia case), when the agent emits a Negado decision, the trace reveal stops at `emitir_decision` (the agent halted on negative finding), the Resultado verdict hero is red, and the justification cites the carencia clause.
- AE4. **Covers R14, R15.** Given INF-003 (missing-docs case), when the agent emits Documentos_Faltantes, Resultado lists `segundo_dictamen` and `examenes_prequirurgicos` as faltantes with friendly Spanish labels, and the deterministic-checks breakdown shows documents required vs attached.
- AE5. **Covers R4, R17.** Given the user has just processed INF-001 and clicks "Volver a la bandeja", when Bandeja re-renders, the "processed" stat tile shows 1, the INF-001 row shows a processed status badge, and the other two informes remain pending.

---

## Success Criteria

- A judge opening the deployed Streamlit URL can pick any of the 3 demo informes, see the agent process, and read a clear verdict in under 60 seconds with no failures or visible Python tracebacks.
- All three demo informes (INF-001 Aprobado, INF-002 Negado, INF-003 Documentos_Faltantes) reach Resultado with the expected verdicts when the backend is healthy.
- The trace timeline animates step-by-step on every run — no all-at-once dump.
- The visual output is recognizably the design: clinical blue palette, Inter Tight typography, the 4-screen flow, the verdict hero treatment.
- A planner picking up this doc can write the implementation plan without inventing product behavior, screen layouts, or backend contract assumptions.

---

## Scope Boundaries

- The Tweaks panel from the design (theme switcher, density toggle, font picker, agent-speed slider) is excluded.
- Real server-sent-events streaming from the backend is excluded — the faux-streamed reveal handles the animation gap without a backend change.
- React, Vite, TypeScript, or any non-Python frontend tooling is excluded.
- Authentication, login, multi-user features are excluded — single demo user.
- Creating new informes, uploading documents, or any Notion writes from the frontend are excluded. The frontend is read-only on `/informes` and only mutates via `/procesar`.
- Translation / i18n is excluded — Spanish only.
- Mobile-specific layouts are excluded — desktop-first, mobile-tolerant only.
- Token-usage telemetry is excluded — the backend does not expose it and we will not ask for it.
- Live token-by-token thinking transcript is excluded — the Procesando screen displays the agent's `final_text` only after the response lands.
- Backend changes (new endpoints, schema migrations, streaming) are excluded — that work belongs to the teammate's track.

---

## Key Decisions

- **Pure Streamlit, no embedded React**: Rationale — the guide mandates Streamlit Community Cloud deployment and Python-only stack. Embedding React-via-Babel works but couples deployment to a single static asset and hides logic from any teammate who only knows Python. Streamlit-native is more maintainable for a 4–6 hour build and aligns with the "fallback monolítico" guidance.
- **Faux-streamed reveal over real SSE**: Rationale — real streaming requires the teammate's backend to expose a streaming endpoint (FastAPI EventSourceResponse) and Streamlit doesn't consume SSE natively (would need a custom JS component or fragment polling). The 5–15s call window is long enough that a post-response reveal feels live to a 30s demo, and the implementation cost is one helper function with `st.empty()` placeholders.
- **Guide-spec API contract over existing `/workspace/app/` shape**: Rationale — the existing `/workspace/app/` backend uses English fields and a single `POST /authorize` endpoint with no exposed trace. Adopting the guide's `GET /informes` + `POST /procesar/{informe_id}` contract lets the frontend match the design's data model directly and aligns with what the teammate is rebuilding to.
- **Stage-routed single page over Streamlit multi-page**: Rationale — Streamlit multi-page apps reset state on navigation, breaking the per-session "processed" tracking and forcing a re-fetch of the informe list. A single page with `st.session_state["stage"]` keeps state persistent across screen transitions.
- **Replace `frontend/index.html` and rewrite `frontend/app.py`**: Rationale — the existing files are the React mock and a Streamlit wrapper for it. Both go away cleanly; nothing in them is reusable for a Streamlit-native rewrite except the design tokens (which we lift into a CSS string).
- **Derive edad client-side, drop sexo from the layout**: Rationale — the backend's `Asegurado` schema has `fecha_nacimiento` only. Computing edad in Python on render is trivial and avoids a teammate dependency. `sexo` is not in the data model and a cedula heuristic would be wrong sometimes; omitting the field is more honest than displaying a guessed value.

---

## Dependencies / Assumptions

- The teammate's FastAPI backend exposes `GET /informes` and `POST /procesar/{informe_id}` with the response shape from the guide. If the contract diverges, the frontend has to adapt — an unverified assumption flagged for planning.
- Notion is seeded with the 3 demo informes (INF-001, INF-002, INF-003) per `seed/populate_notion.py` in the guide.
- The Anthropic API key is funded with at least $5 USD per the guide so the demo doesn't run out mid-judging.
- Render free tier sleeps after 15 minutes; the deployment plan must include a wake-up ping before the demo (per the guide).
- Streamlit Community Cloud accepts the build with `frontend/requirements.txt` containing `streamlit` and `requests`.
- The current `app/` directory contains an earlier backend with a different schema. The frontend codes against the guide spec; the teammate is responsible for reconciling.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R10][Technical] The exact step-reveal cadence (250ms? variable per tool?) is a polish call best made when seeing the animation in a browser.
- [Affects R15][Technical] Whether the deterministic-checks breakdown is rendered from a parsed trace or from explicit fields the backend returns — depends on what's easiest given the trace shape.
- [Affects R18][Needs research] Streamlit's CSS injection has known limitations on certain widgets (file uploaders, dataframes). Confirm during planning that the components needed for each screen accept the design's styling.
- [Affects R3, R4][Technical] Whether to cache `GET /informes` (`st.cache_data`) or refetch on every Bandeja render — a small UX call about staleness vs latency.
