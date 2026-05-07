---
title: Pre-Autorización Quirúrgica · Streamlit Frontend
type: feat
status: active
date: 2026-05-07
origin: docs/brainstorms/frontend-preauth-streamlit-requirements.md
---

# Pre-Autorización Quirúrgica · Streamlit Frontend

## Summary

Replace the existing React/Babel `frontend/index.html` with a pure-Streamlit application that recreates the design's 4-screen flow (Bandeja → Detalle → Procesando → Resultado), wires it to the FastAPI backend's guide-spec contract, and renders the trace timeline through a faux-streamed reveal driven by `st.empty()` placeholders. The implementation splits screens into modules under `frontend/screens/` with shared CSS, API, and state utilities at the package root.

---

## Problem Frame

A previous pass dropped the design's React/Babel mock into `frontend/` without going through brainstorm → plan → work → review. The mock is unwired, the guide mandates Streamlit Community Cloud deployment, and the teammate is rebuilding the FastAPI backend to the guide's spec. Implementation needs to replace the mock with a Streamlit-native frontend, preserve the design's clinical aesthetic and the trace-animation moment, and stay fully decoupled from the teammate's backend timeline by coding strictly to the published API contract. (See origin: `docs/brainstorms/frontend-preauth-streamlit-requirements.md`.)

---

## Requirements

- R1. Stage-routed single Streamlit page with `st.session_state` driving Bandeja → Detalle → Procesando → Resultado transitions and back-navigation (origin R1, R2)
- R2. Bandeja fetches and displays informes from `GET /informes` with three stat tiles and per-row entry into Detalle (origin R3, R4)
- R3. Detalle renders patient/policy/procedure/documents panels plus the 6-step "Agente listo" preview with a primary "Procesar" CTA (origin R5, R6, R7)
- R4. Procesando renders the 6 tool-step placeholders, calls `POST /procesar/{informe_id}` with a 120-second timeout, and reveals each actual trace entry sequentially with a small delay once the response lands (origin R8, R9, R10, R11)
- R5. Resultado renders verdict hero, justificación, cláusula aplicada, decision ID, friendly-labeled missing documents when applicable, deterministic-checks breakdown, and a full-trace expander (origin R13, R14, R15, R16, R17)
- R6. Backend errors and unreachable states render a clear in-screen error with backend URL and a retry affordance, never a Python traceback (origin R12)
- R7. The app's visual identity — palette, typography, layout, component shapes — matches the design's clinical aesthetic via a single injected CSS block (origin R18, R19)
- R8. The frontend reads `BACKEND_URL` from `st.secrets["BACKEND_URL"]` with `os.getenv("BACKEND_URL", "http://localhost:8000")` as fallback (origin R20)
- R9. The frontend codes only against the guide-spec contract for `GET /informes` and `POST /procesar/{informe_id}` (origin R21)

**Origin actors:** A1 (hackathon judge), A2 (Streamlit frontend), A3 (FastAPI backend)
**Origin flows:** F1 (inspect and process an informe), F2 (backend unavailable)
**Origin acceptance examples:** AE1 (covers R12), AE2 (covers R8/R9/R10), AE3 (covers R10/R13), AE4 (covers R14/R15), AE5 (covers R4/R17)

---

## Scope Boundaries

- Tweaks panel from the design (theme/density/font/agent-speed) is excluded (origin)
- Real SSE/streaming from backend is excluded (origin)
- React, Vite, TypeScript, or any non-Python frontend tooling is excluded (origin)
- Authentication, login, multi-user is excluded (origin)
- Creating informes, uploading docs, any Notion writes from the frontend are excluded (origin)
- i18n / translation is excluded — Spanish only (origin)
- Mobile-specific layouts are excluded — desktop-first, mobile-tolerant only (origin)
- Token-usage telemetry is excluded — not exposed by the backend (origin)
- Live token-by-token thinking transcript is excluded — `final_text` is shown post-response only (origin)
- Backend changes (new endpoints, schema migrations, streaming) are excluded — teammate's track (origin)

### Deferred to Follow-Up Work

- Automated UI testing (Playwright, Streamlit AppTest beyond pure functions): Streamlit AppTest is workable but adds harness complexity disproportionate to a hackathon timeline. Manual verification of all 3 demo cases against the live backend is the v1 acceptance gate.
- Telemetry / analytics (page views, time-to-decision tracking): out of scope for hackathon submission.

---

## Context & Research

### Relevant Code and Patterns

- `frontend/app.py` (current) — Streamlit wrapper that mounts the React HTML via `st.components.v1.html`. Will be entirely rewritten.
- `frontend/index.html` (current) — React/Babel mock with all visual decisions inlined. Source of truth for design tokens, color palette, typography stack, and layout proportions. Lift CSS variables and component shapes from it; discard the React structure.
- `frontend/.streamlit/secrets.toml.example` (current) — already carries `BACKEND_URL` example; keep convention.
- `frontend/requirements.txt` (current) — already pins `streamlit==1.39.0`, `requests==2.32.3`. Sufficient; no new deps needed.
- `hackiathon_preauth_guia.md` — guide-spec API contract authoritative reference (`GET /informes` shape and `POST /procesar/{informe_id}` response shape).
- Design bundle reference (`/tmp/design_extract/hackiathon-1/project/data.jsx`) — the mocked `buildPolicyOutcome()` and `INFORMES` array show the exact data shape the trace renders against. Used for translating mock data structure into expected backend response handling, then discarded.

### Institutional Learnings

- `docs/solutions/` does not exist in this repo. No prior learnings to reuse.

### External References

- Streamlit `st.session_state` for stage routing across reruns: standard pattern, no version-specific concerns at 1.39.0.
- Streamlit `st.empty()` placeholder pattern for progressive content reveal: standard pattern, supports any widget rerender.
- Streamlit custom CSS via `st.markdown(unsafe_allow_html=True)`: works for layout, color, typography on top-level containers and `st.markdown` HTML; widgets that render in iframes (e.g., dataframes, file uploaders) resist external CSS — this plan does not use those.

---

## Key Technical Decisions

- **Modular layout under `frontend/`**: Single-file is simpler but a 4-screen app with shared CSS, API client, and state helpers earns split modules. Each screen lives in `frontend/screens/<name>.py`; shared concerns live at `frontend/` root (`api.py`, `state.py`, `styles.py`, `components.py`, `utils.py`). Rationale: testable pure modules, clearer review surface, no deep nesting.
- **Faux-streamed reveal via `st.empty()` placeholders + `time.sleep(0.2)`**: One placeholder per expected tool step; on response, replace each placeholder's content with the actual trace entry, sleeping ~200ms between updates. Rationale: blocks the page during the reveal, which is the desired UX (~1.2s of choreographed reveal after the 5–15s call). 200ms is the default constant `STEP_REVEAL_DELAY_S`; tunable in code, not via UI.
- **Parse deterministic-checks breakdown from the trace, not from new backend fields**: Resultado's carencia and documents breakdowns are extracted from `verificar_carencia` and `validar_documentos` trace entries. Rationale: keeps the backend contract minimal; the data we need is already in the trace.
- **Refetch `/informes` on every Bandeja entry; no cross-render cache**: Avoids `st.cache_data` to prevent stale state between processing runs (the per-session "processed" stat must reflect just-completed runs). Single fetch per Bandeja render is acceptable latency-wise; the call is cheap relative to the agent processing call.
- **Per-session "processed" tracking via `st.session_state["processed_ids"]` set**: Origin requires Bandeja's processed counter to update after Resultado → Volver. Storing processed informe IDs in session state and intersecting with the live `/informes` list at render time is simpler than augmenting the fetch.
- **Edad derived client-side from `fecha_nacimiento`; sexo omitted**: Confirmed during brainstorm. Rationale lives in the origin doc.
- **CSS lift, not import**: Copy the design's CSS variables, base type, and component classes into `frontend/styles.py` as a Python string constant. Rationale: avoids a CSS file fetch (Streamlit Cloud doesn't serve static assets the same way), keeps the deploy a pure-Python bundle.
- **`requests` over `httpx`**: Already pinned; the guide example uses it; sync HTTP is fine because Streamlit script execution is sync per rerun. No async needed.

---

## Open Questions

### Resolved During Planning

- *Module layout (single-file vs split)*: Resolved as split — `frontend/screens/` for screen modules, `frontend/{api,state,styles,components,utils}.py` for shared concerns.
- *Cache strategy for `/informes`*: Resolved as no cache — refetch on Bandeja render.
- *Deterministic-checks data source*: Resolved as parse-from-trace, not new backend fields.

### Deferred to Implementation

- *Exact step-reveal cadence*: Default 200ms; tune by feel during manual verification of the 3 demo cases.
- *Whether to render the procesando placeholders all-grey or pre-named with each tool*: Try named (each placeholder shows the tool name greyed out) first; if too busy, fall back to anonymous numbered slots.
- *Mobile-tolerance threshold*: Implement desktop-first; verify it's at least readable at iPhone widths during manual check.

---

## Output Structure

    frontend/
    ├── app.py                      # entry: state init, CSS inject, stage switch
    ├── api.py                      # backend client (fetch_informes, procesar_informe)
    ├── state.py                    # session state init + transition helpers
    ├── styles.py                   # CSS string constant lifted from design
    ├── components.py               # reusable UI helpers (badge, stat tile, panel header, doc chip)
    ├── utils.py                    # fmt_date, calc_edad, DOC_LABEL, decision tone, parse helpers
    ├── screens/
    │   ├── __init__.py
    │   ├── bandeja.py
    │   ├── detalle.py
    │   ├── procesando.py
    │   └── resultado.py
    ├── tests/
    │   ├── __init__.py
    │   ├── test_api.py             # mocks HTTP, asserts client behavior
    │   ├── test_utils.py           # pure-function unit tests
    │   └── test_state.py           # session state transition helpers
    ├── .streamlit/
    │   ├── secrets.toml            # gitignored, lives at runtime
    │   └── secrets.toml.example    # already exists
    └── requirements.txt            # already exists

The legacy `frontend/index.html` is removed as part of U1.

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

**Stage routing:**

```
app.py rerun:
  init_state_if_needed()
  inject_css_once()
  match state.stage:
    "bandeja"    -> screens.bandeja.render()
    "detalle"    -> screens.detalle.render(state.selected_informe_id)
    "procesando" -> screens.procesando.render(state.selected_informe_id)
    "resultado"  -> screens.resultado.render(state.last_result)
```

**Faux-streamed reveal in Procesando:**

```
render():
  show timeline header, six placeholders = [st.empty() for _ in tool_names]
  set placeholder i to "pending" visual
  call api.procesar_informe(informe_id)  # 5-15s, blocks
  for i, trace_entry in enumerate(response.trace):
    placeholder[i].markdown(rendered_step(trace_entry, status="ok"))
    time.sleep(STEP_REVEAL_DELAY_S)
  state.last_result = response
  state.stage = "resultado"
  st.rerun()
```

**Verdict tone mapping in Resultado:**

| `decision.decision`       | hero tone |
|---------------------------|-----------|
| `Aprobado`                | green     |
| `Negado`                  | red       |
| `Documentos_Faltantes`    | amber     |

---

## Implementation Units

### U1. Project scaffolding and module skeleton

**Goal:** Create the new module layout, remove the legacy React mock, and ensure the app starts (renders an empty Bandeja shell) before any feature code lands.

**Requirements:** R1, R8

**Dependencies:** none

**Files:**
- Create: `frontend/api.py`, `frontend/state.py`, `frontend/styles.py`, `frontend/components.py`, `frontend/utils.py`
- Create: `frontend/screens/__init__.py`, `frontend/screens/bandeja.py`, `frontend/screens/detalle.py`, `frontend/screens/procesando.py`, `frontend/screens/resultado.py`
- Create: `frontend/tests/__init__.py`
- Modify: `frontend/app.py` (rewrite from React-mount wrapper to stage-switch entry)
- Delete: `frontend/index.html`

**Approach:**
- New `app.py` calls `st.set_page_config`, reads `BACKEND_URL` (secrets-then-env fallback), runs `state.init_session()`, injects CSS once via `styles.inject()`, then dispatches by `state.stage`.
- Each screen module exports a `render(...)` function. v1 returns `st.write("<screen> placeholder")`.
- All modules are syntactically valid empty stubs so a `streamlit run frontend/app.py` boots without error.

**Patterns to follow:**
- Existing `frontend/.streamlit/secrets.toml.example` for secret naming.
- Guide's `frontend/app.py` example (in `hackiathon_preauth_guia.md`) for `st.set_page_config` and secrets convention.

**Test scenarios:**
- Test expectation: none — pure scaffolding, no behavior to assert beyond "app boots".

**Verification:**
- `streamlit run frontend/app.py` starts without ImportError or AttributeError; landing page shows the Bandeja placeholder text.
- `frontend/index.html` no longer exists.

---

### U2. Design tokens and global CSS

**Goal:** Lift the design's CSS variables, base typography, layout primitives, and component classes (badges, buttons, cards) into a single CSS string injected once per session.

**Requirements:** R7

**Dependencies:** U1

**Files:**
- Modify: `frontend/styles.py`

**Approach:**
- Copy CSS variables verbatim from `frontend/index.html` (current React mock) `:root` block and dark-sidebar overrides — palette (`--bg`, `--ink`, `--brand`, semantic good/warn/bad), radius, shadow, typography stack (Inter Tight + JetBrains Mono + Instrument Serif from Google Fonts).
- Include `<link>` tags to Google Fonts inside the injected HTML so fonts load in Streamlit's iframe.
- Add layout primitives Streamlit needs: `.app-shell`, `.content`, `.card`, `.card-b`, `.row`, `.col`, `.stat-tile`, `.panel-title`, `.badge.{good,warn,bad,brand,neutral}`, `.btn-primary`, `.timeline-step` (for procesando), `.verdict-hero.{good,bad,warn}` (for resultado).
- Export `CSS: str` constant and `inject() -> None` that calls `st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)` plus the Google Fonts link.
- Delete the legacy mock's React-specific CSS (e.g., tweaks-panel theming) — out of scope per origin.

**Patterns to follow:**
- Design's existing `:root` tokens — preserve hex values exactly so verdict-hero greens/reds match the screenshots.

**Test scenarios:**
- Test expectation: none — visual asset; verified by running the app and comparing to the design HTML side-by-side during manual check.

**Verification:**
- After `inject()`, page chrome uses Inter Tight (visible in browser DevTools) and the brand blue `#1763d1` resolves on `.btn-primary`.
- No console errors about CSS parsing.

---

### U3. Backend API client

**Goal:** Encapsulate `GET /informes` and `POST /procesar/{informe_id}` behind clean Python functions with timeout, error normalization, and a `BackendError` type that screens can catch and render.

**Requirements:** R2, R4, R6, R8, R9 — covers AE1, AE2

**Dependencies:** U1

**Files:**
- Modify: `frontend/api.py`
- Create: `frontend/tests/test_api.py`

**Approach:**
- `api.py` reads `BACKEND_URL` once at import time from `st.secrets` with `os.environ` fallback (matches guide convention).
- `fetch_informes() -> list[InformeListItem]`: GET `/informes` with 20s timeout; raises `BackendError` on non-2xx, network error, timeout, or malformed JSON.
- `procesar_informe(informe_id: str) -> ProcesarResponse`: POST `/procesar/{informe_id}` with 120s timeout (matches guide); same error normalization.
- Use `dataclass` (or `TypedDict`) types `InformeListItem`, `ProcesarResponse`, `Decision`, `TraceEntry` for typed shape — keeps screens out of dict-key-archaeology.
- `BackendError` carries `kind: Literal["network", "timeout", "http", "decode"]`, `status: int | None`, `message: str`, `url: str` — error UI uses these fields.
- No retry inside the client; retry is a screen-level decision (rerun via state).

**Patterns to follow:**
- `requests.get(..., timeout=N)` and `r.raise_for_status()` per the guide's example `frontend/app.py` in `hackiathon_preauth_guia.md`.

**Test scenarios:**
- Happy path: `fetch_informes()` parses 3 informes from mock 200 response → returns `list[InformeListItem]` of length 3 with expected fields.
- Happy path: `procesar_informe("INF-001")` parses a response with trace + decision → returns `ProcesarResponse` with all decision fields populated.
- Error path: 500 response → raises `BackendError(kind="http", status=500)`.
- Error path: connection refused → raises `BackendError(kind="network")`.
- Error path: timeout → raises `BackendError(kind="timeout")`.
- Error path: malformed JSON in 200 → raises `BackendError(kind="decode")`.
- Edge case: `procesar_informe` response with `decision=null` (agent didn't emit) → returns response with `decision=None`, doesn't raise.

**Verification:**
- All 7 tests pass via `pytest frontend/tests/test_api.py`.
- Hand-running against a stubbed local FastAPI returning the guide's contract returns expected dataclasses.

---

### U4. Session state init and transition helpers

**Goal:** Centralize all `st.session_state` access — initial keys, stage transitions, and the per-session "processed_ids" set — so screens never touch raw session state.

**Requirements:** R1

**Dependencies:** U1, U3

**Files:**
- Modify: `frontend/state.py`
- Create: `frontend/tests/test_state.py`

**Approach:**
- `init_session()` sets defaults if missing: `stage="bandeja"`, `selected_informe_id=None`, `last_result=None`, `processed_ids: set[str]=set()`, `last_error: BackendError | None=None`.
- `go_to_detalle(informe_id)`, `go_to_procesando(informe_id)`, `go_to_resultado(result)`, `go_to_bandeja()` — transition functions that update state and call `st.rerun()`.
- `mark_processed(informe_id)` — adds to `processed_ids`.
- `is_processed(informe_id) -> bool`, `processed_count(informe_ids: list[str]) -> int` — pure read helpers.
- All transitions reset `last_error` to None (errors are screen-scoped).
- Use a `MockSessionState` dict-subclass in tests; `state.py` imports `st.session_state` indirectly via a tiny accessor so tests can inject a mock.

**Patterns to follow:**
- Streamlit idiom of guarding `if "key" not in st.session_state` for one-time init.

**Test scenarios:**
- Happy path: `init_session()` on empty state populates defaults; calling twice is idempotent.
- Happy path: `mark_processed("INF-001")` then `is_processed("INF-001")` → True; for unmarked → False.
- Happy path: `processed_count(["INF-001", "INF-002", "INF-003"])` after marking INF-001 and INF-003 → 2.
- Edge case: transitions clear `last_error` to None.
- Edge case: `processed_count` with empty list → 0.

**Verification:**
- All tests pass via `pytest frontend/tests/test_state.py`.

---

### U5. Bandeja screen

**Goal:** Render the inbox of informes with stat tiles (total / processed / pending), per-row preview of `id_informe`, `descripcion_procedimiento`, `hospital`, and a click affordance that transitions to Detalle.

**Requirements:** R2 — covers AE5

**Dependencies:** U1, U2, U3, U4

**Files:**
- Modify: `frontend/screens/bandeja.py`, `frontend/components.py`

**Approach:**
- `render()` calls `api.fetch_informes()`. On `BackendError`, render `components.error_panel(err)` with retry button (sets `state.stage="bandeja"` again to force rerender) and return.
- Stat tiles row: total = `len(informes)`, processed = `state.processed_count([i.id_informe for i in informes])`, pending = total − processed. Each tile uses `components.stat_tile(label, value, tone)`.
- For each informe, render a card row: id chip + descripcion + hospital + status badge (`procesado` if id in `processed_ids`, else `pendiente`). Use `st.button` with `key=f"open_{id}"` and `on_click=state.go_to_detalle(id)`.
- Sort informes alphabetically by `id_informe` for stable order across reruns.

**Patterns to follow:**
- Custom CSS classes from U2 (`.stat-tile`, `.card`, `.badge.brand`, `.badge.good`).

**Test scenarios:**
- Test expectation: none for the screen render itself (Streamlit UI).
- Pure helper coverage lives in `test_state.py` for `processed_count` (already in U4).

**Verification:**
- Manual: with backend up and 3 informes seeded, all 3 rows visible with correct hospital/descripcion/id.
- Manual: clicking a row transitions to Detalle for that informe.
- Manual: with backend down, error panel renders with backend URL visible and retry button works.
- Manual: after processing INF-001 and returning, processed tile reads 1, INF-001 row shows the procesado badge (covers AE5).

---

### U6. Detalle screen

**Goal:** Render patient/policy/procedure/documents panels for the selected informe and the "Agente listo" preview card listing the 6 tool steps; primary "Procesar pre-autorización" CTA transitions to Procesando.

**Requirements:** R3

**Dependencies:** U1, U2, U3, U4, U5

**Files:**
- Modify: `frontend/screens/detalle.py`, `frontend/components.py`, `frontend/utils.py`

**Approach:**
- `render(informe_id)`: backend doesn't expose a single-informe GET, so fetch the list and find the matching one. (List size is ~3, the cost is negligible.)
- Four panels via `components.panel(title, rows)`:
  - **Paciente:** cédula, nombre, edad (computed via `utils.calc_edad(fecha_nacimiento)`).
  - **Póliza:** número, plan (with level badge), fecha de alta (`utils.fmt_date`), estado (with status badge).
  - **Procedimiento:** CPT, descripción, fecha programada, urgencia, justificación clínica.
  - **Documentos adjuntos:** list of friendly labels via `utils.DOC_LABEL[code]`.
- "Agente listo" card lists the 6 tool steps (hardcoded constant `AGENT_TOOLS` in `utils.py`): `get_informe_medico`, `get_poliza_paciente`, `get_cobertura`, `verificar_carencia`, `validar_documentos`, `emitir_decision` — each with a one-line Spanish description.
- Primary CTA: `st.button("Procesar pre-autorización", type="primary", on_click=state.go_to_procesando, args=(informe_id,))`.
- "Volver" secondary button → `state.go_to_bandeja()`.

**Patterns to follow:**
- `components.panel` mirrors the design's `.card` + `.panel-title` shape from `frontend/index.html`.

**Test scenarios:**
- `utils.calc_edad("1985-05-12")` against current date `2026-05-07` → 40. (Pure unit test.)
- `utils.calc_edad("1985-05-12")` against `2026-05-13` → 41. (Boundary day-after-birthday.)
- `utils.fmt_date("2024-05-07")` → `"07 may 2024"` (Spanish locale shape; exact output verified per implementation).
- `utils.DOC_LABEL["informe_quirurgico"]` → `"Informe quirúrgico"`. (Lookup test for all 5 known doc codes.)
- Edge case: `utils.DOC_LABEL.get("unknown_code", code)` returns the code itself as fallback.
- All scenarios live in `frontend/tests/test_utils.py`.

**Verification:**
- All `test_utils.py` tests pass.
- Manual: navigating into INF-001 shows Juan Pérez Andrade, age computed correctly, Plan Salud Premium with level badge, all four panels populated.
- Manual: "Procesar" CTA transitions to Procesando.

---

### U7. Procesando screen with faux-streamed reveal

**Goal:** Render the 6-step placeholder timeline, call `POST /procesar/{informe_id}`, then reveal each actual trace entry sequentially with ~200ms delays before transitioning to Resultado.

**Requirements:** R4 — covers AE2, AE3

**Dependencies:** U1, U2, U3, U4, U6

**Files:**
- Modify: `frontend/screens/procesando.py`, `frontend/components.py`, `frontend/utils.py`

**Execution note:** Implement against a local stub backend (e.g., a 30-line FastAPI returning hardcoded fixtures) before the teammate's backend is ready. The reveal mechanism's correctness is verifiable without the real agent.

**Approach:**
- `STEP_REVEAL_DELAY_S = 0.2` constant in `screens/procesando.py`.
- `render(informe_id)`:
  1. Header: informe id, hospital, "Agente analizando..." text + an indeterminate spinner.
  2. Build six `st.empty()` placeholders, one per `AGENT_TOOLS` entry (ordered). Pre-fill each with `components.timeline_step(tool_name, status="pending")`.
  3. Track `start_ts = time.time()`. Call `api.procesar_informe(informe_id)` inside `try/except BackendError` — on error, render `components.error_panel(err)` with retry (re-enter procesando) and "Volver a la bandeja" buttons; do NOT transition.
  4. On success, walk `response.trace`: for each entry, find the matching placeholder by `entry.tool` name, call `placeholder.markdown(timeline_step(entry, status="ok"))`, then `time.sleep(STEP_REVEAL_DELAY_S)`.
  5. Steps that don't appear in the trace (agent halted early) stay in their pending visual — leave them greyed.
  6. Update telemetry footer (elapsed = `time.time() - start_ts`, step count = `len(trace)`).
  7. `state.go_to_resultado(response)`; `state.mark_processed(informe_id)`.
- Note: `state.go_to_*` performs `st.rerun()`, so the screen function returns naturally.

**Patterns to follow:**
- `st.empty()` placeholder pattern (Streamlit standard).
- Design's `.timeline-step` CSS classes from U2.

**Test scenarios:**
- `screens.procesando._match_placeholders(trace, tool_order)` (extract a pure helper that maps trace entries to placeholder indices) — pure tests:
  - Happy path: full 6-tool trace → returns 6 (index, entry) pairs in tool order.
  - Edge case: 4-tool trace ending in `emitir_decision` (agent halted on cobertura/carencia) → returns 4 pairs; missing tools not present in the result. (Covers AE3 expectation that early-halt traces don't render fake later steps.)
  - Edge case: trace entry with unknown tool name → that entry is dropped from the mapping (and a debug-level note logged), no exception raised.
- Verification of the reveal animation itself is manual — the timing is a feel call.

**Verification:**
- All `_match_placeholders` tests pass.
- Manual: INF-001 (Aprobado, 6 tools) reveals 6 steps in order, each ~200ms apart, then lands on Resultado.
- Manual: INF-002 (Negado on carencia, ~5 tools, halts at `emitir_decision`) reveals only the actual trace entries; unused step placeholders stay greyed.
- Manual: simulated backend timeout shows the in-screen error panel with retry, no Python traceback.

---

### U8. Resultado screen

**Goal:** Render the verdict hero, justification, cláusula aplicada, decision ID, missing-document chips when applicable, deterministic-checks breakdown derived from the trace, and a full-trace expander; back-to-bandeja affordance.

**Requirements:** R5 — covers AE4, AE5

**Dependencies:** U1, U2, U3, U4, U7

**Files:**
- Modify: `frontend/screens/resultado.py`, `frontend/components.py`, `frontend/utils.py`

**Approach:**
- `render(result)` reads from `state.last_result` (which `result` aliases).
- Verdict hero: `utils.decision_tone(result.decision.decision)` returns `"good" | "bad" | "warn"`; component `components.verdict_hero(decision_label, tone, justificacion)`.
- Sub-panel: cláusula aplicada (mono font), decision ID (mono).
- If decision is `Documentos_Faltantes`: render document chips using `utils.DOC_LABEL` for friendly labels.
- Deterministic-checks breakdown: `utils.parse_carencia_check(trace) -> {dias_transcurridos, dias_requeridos, cumple} | None` and `utils.parse_documentos_check(trace) -> {requeridos, adjuntos, faltantes} | None`. Render as compact two-row layout using badges (good/bad) where applicable.
- Full-trace expander (`st.expander`) lists each trace entry with tool name, input dict, output dict in `st.json` blocks.
- "Volver a la bandeja" button → `state.go_to_bandeja()`.

**Patterns to follow:**
- Design's verdict hero treatment from `frontend/index.html` (current React mock) — green for Aprobado, red for Negado, amber for Documentos_Faltantes.

**Test scenarios:**
- `utils.decision_tone("Aprobado")` → `"good"`; `"Negado"` → `"bad"`; `"Documentos_Faltantes"` → `"warn"`; unknown → `"neutral"`.
- `utils.parse_carencia_check(trace_with_carencia_entry)` returns expected dict; without entry returns `None`.
- `utils.parse_documentos_check(trace_with_validar_documentos_entry)` returns dict with `faltantes` matching the trace output; without entry returns `None`.
- Edge case: `parse_carencia_check` with malformed entry (missing fields) returns `None`, doesn't raise.
- Tests in `frontend/tests/test_utils.py`.

**Verification:**
- Tests pass.
- Manual: INF-001 → green Aprobado hero with justificación and clausula; trace expander has 6 entries.
- Manual: INF-002 → red Negado hero, carencia breakdown shows e.g. 45 / 365 with red bad-badge (covers AE3 result-side).
- Manual: INF-003 → amber Docs faltantes hero, faltantes chips show "Segundo dictamen médico" and "Exámenes prequirúrgicos" with friendly labels (covers AE4).
- Manual: clicking "Volver a la bandeja" returns to Bandeja and the just-processed informe shows processed badge (covers AE5).

---

### U9. Error states polish and end-to-end smoke

**Goal:** Tighten error/empty states across screens, verify the full flow against the live backend with all 3 demo cases, and resolve any visual fidelity gaps surfaced during manual review.

**Requirements:** R6, R7

**Dependencies:** U2, U3, U4, U5, U6, U7, U8

**Files:**
- Modify: `frontend/components.py` (error panel polish), individual screens for any UX gaps caught during smoke test

**Approach:**
- `components.error_panel(err: BackendError, *, on_retry=None)`: renders icon + Spanish error title (e.g., "No se pudo conectar al backend"), backend URL in mono font, raw message in a collapsed expander, retry button when `on_retry` is provided.
- Empty-list case in Bandeja: if `/informes` returns `[]`, render an empty-state card pointing to the seeding script in the guide.
- Smoke test: with backend live, run all 3 demo informes end-to-end; record any visual or copy gaps as TODOs and address inside this unit. Do not extend scope to new features.
- Spanish copy review: every user-facing string in Spanish; no English leakage.

**Test scenarios:**
- Test expectation: no new unit tests — this is integration polish. Existing unit tests stay green.

**Verification:**
- All 3 demo cases reach the expected verdict (Aprobado / Negado / Documentos_Faltantes).
- Backend-down state shows the polished error panel on every screen that can hit it.
- Empty `/informes` shows the dedicated empty-state, not a blank list.
- `pytest frontend/tests/` is green.
- A screenshot side-by-side against the original design HTML shows the same palette, type, and overall shape on each screen.

---

## System-Wide Impact

- **Interaction graph:** Streamlit reruns the entire `app.py` script on each user action. Stage transitions are state writes followed by `st.rerun()`; screens must be idempotent across reruns. Module imports happen once per process; `BACKEND_URL` resolves at import time.
- **Error propagation:** All HTTP errors are normalized to `BackendError` in `api.py`. Screens catch and render via `components.error_panel`; no error bubbles to a Streamlit traceback. `state.last_error` is per-screen scratch; transitions clear it.
- **State lifecycle risks:** `processed_ids` lives only in session state — clearing the browser tab resets the demo. Acceptable; not a multi-user app. `last_result` is large (full trace) but only one is held at a time.
- **API surface parity:** None — `api.py` is the single boundary to the backend. If the teammate ships a different shape, only `api.py` and its tests change.
- **Integration coverage:** The faux-streamed reveal coordinates `api.procesar_informe` (sync, 5–15s) and `time.sleep` reveals against `st.empty().markdown` updates. This timing relationship is verified by manual smoke against the live backend, not unit tests — Streamlit's render loop is hostile to traditional UI tests at this scope.
- **Unchanged invariants:** The teammate's FastAPI backend, Notion seeding, the guide's API contract, and the `/workspace/app/` directory are explicitly untouched by this plan. The deploy story (Streamlit Community Cloud) is unchanged from the guide.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Teammate's backend ships a different shape than the guide spec | `api.py` is the single integration point; revisions are localized. Develop against a 30-line FastAPI stub locally until the real backend stabilizes. |
| Streamlit CSS injection has limits (some widgets render in iframes) | Plan uses only top-level Markdown/HTML, layout containers, and buttons — all of which accept the design tokens. No `st.dataframe`, file uploaders, or other iframe-rendered widgets. |
| `time.sleep` blocks the Streamlit script during reveal — perceived hang if it runs too long | Total reveal budget = `STEP_REVEAL_DELAY_S × 6 = 1.2s`. Tunable; if the demo feels slow, drop to 150ms. |
| Render free-tier backend sleeps — first call after idle takes ~30s | Out of scope per origin (deployment is the guide's concern), but error panel surfaces backend URL so a judge can hit `/health` to wake it. |
| Manual UI verification only — no automated regression net | Accepted for hackathon scope. Pure-function tests cover the parts that *can* break silently (date math, parsing, state transitions). |
| Existing `app/` backend uses different schema and may conflict | Documented in origin Dependencies / Assumptions; teammate's track. Frontend never imports from `app/`. |

---

## Documentation / Operational Notes

- Update repo `README.md` only if the existing description of the frontend stops being accurate after the rewrite. Defer until U9.
- The guide's existing deployment instructions for Streamlit Community Cloud remain valid; no doc updates required for deploy.
- No new env vars beyond `BACKEND_URL` (already documented).

---

## Sources & References

- **Origin document:** `docs/brainstorms/frontend-preauth-streamlit-requirements.md`
- Guide: `hackiathon_preauth_guia.md` (API contract, demo cases, deployment)
- Design source (extracted from the design URL): `/tmp/design_extract/hackiathon-1/project/` — CSS tokens, component shapes, mocked data structure for reference during U2 / U6 / U7 / U8 (this directory is volatile; copy any tokens needed into `frontend/styles.py` rather than referencing it at runtime)
- Existing files: `frontend/index.html` (to be deleted), `frontend/app.py` (to be rewritten), `frontend/.streamlit/secrets.toml.example`, `frontend/requirements.txt`
