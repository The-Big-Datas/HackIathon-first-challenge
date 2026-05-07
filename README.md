# Insurance Pre-Authorization Agent

Agente FastAPI + Claude (SDK Anthropic) que decide en segundos si un informe
medico se **Aprueba**, **Niega** o requiere **Documentos_Faltantes**. Lee
informes, polizas y coberturas desde **Notion** y persiste la decision en una
DB de auditoria.

## Arquitectura

```
POST /authorize  (id_informe, cedula)
      |
      v
PreAuthorizationAgent  (Anthropic tool-use loop, adaptive thinking, prompt caching)
      |
      +-- tool: fetch_informe       --> Notion (Informes_Medicos + Asegurados)
      +-- tool: fetch_cobertura     --> Notion (Asegurados + Polizas + Planes + Coberturas)
      +-- tool: submit_decision     --> Notion (Decisiones)
```

Flujo deterministico que sigue el agente, en este orden:

1. `fetch_informe(id_informe)` y validar que `paciente.cedula` coincida con la del request.
2. `fetch_cobertura(cedula, procedimiento_cpt)`.
3. **Vigencia**: `poliza.estado == "Vigente"`.
4. **Cobertura**: existe cobertura para el plan + procedimiento y `cubierto == true`.
5. **Carencia**: dias desde `poliza.fecha_alta` >= `cobertura.dias_carencia`.
6. **Documentos**: `cobertura.documentos_requeridos` ⊆ `informe.documentos_adjuntos`.
7. `submit_decision(...)` con la conclusion.

Detiene en el primer paso fallido.

## Estructura

```
backend/
├── .env.example
├── requirements.txt
└── app/
    ├── main.py                     # FastAPI app + CORS + /health
    ├── config.py                   # Carga de .env
    ├── models/schemas.py           # AuthorizeRequest / AuthorizeResponse / Decision
    ├── services/
    │   ├── notion_service.py       # Lecturas/escrituras a Notion
    │   └── agent_service.py        # Loop Anthropic + tools
    └── routers/authorization.py    # POST /authorize
docs/notion_setup.md                # Como crear la integracion + sembrar DBs
seed/populate_notion.py             # Crea las 6 DBs y siembra datos demo
```

## Setup

### 1. Notion (una sola vez)

Sigue [`docs/notion_setup.md`](docs/notion_setup.md):

1. Crea integracion interna en Notion y copia el `NOTION_TOKEN`.
2. Crea una pagina padre y conecta la integracion.
3. `cp backend/.env.example backend/.env` y rellena `NOTION_TOKEN` +
   `NOTION_PARENT_PAGE_ID`.
4. Corre el seed:
   ```bash
   pip install -r backend/requirements.txt
   python seed/populate_notion.py
   ```
5. Pega los 6 IDs `NOTION_DB_*` que imprime en `backend/.env`.

El seed deja en Notion: 3 planes, 8 coberturas, 3 asegurados, 3 polizas, 3
informes y la DB de decisiones vacia.

### 2. API key de Anthropic

Agrega `ANTHROPIC_API_KEY=sk-ant-...` en `backend/.env`. El modelo por defecto
es `claude-sonnet-4-6` (cambialo con `CLAUDE_MODEL`).

### 3. Ejecutar

```bash
cd backend
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

## Uso

### POST /authorize

Request:
```json
{
  "id_informe": "INF-001",
  "cedula": "0912345678"
}
```

Response (ejemplo aprobado):
```json
{
  "id_informe": "INF-001",
  "cedula": "0912345678",
  "decision": "Aprobado",
  "justificacion": "Procedimiento 44970 cubierto por Plan Salud Premium. Carencia de 30 dias cumplida (730 dias transcurridos). Documentos completos.",
  "clausula_aplicada": "cobertura vigente y documentacion completa",
  "documentos_faltantes": [],
  "id_decision": "DEC-INF-001-1714800000",
  "timestamp": "2026-05-07T18:30:00+00:00"
}
```

### Escenarios de prueba (seed incluido)

| `id_informe` | `cedula`     | Decision esperada       | Por que |
|--------------|--------------|-------------------------|---------|
| `INF-001`    | `0912345678` | `Aprobado`              | Premium + 2 anios + documentos completos |
| `INF-002`    | `0923456789` | `Negado`                | Estandar + 45 dias < carencia 365 dias (cirugia bariatrica) |
| `INF-003`    | `0934567890` | `Documentos_Faltantes`  | Falta `examenes_prequirurgicos`, `segundo_dictamen` |
| `INF-001`    | `9999999999` | `Negado`                | Cedula no coincide con paciente del informe |

## Modelo de datos en Notion

6 databases relacionadas (creadas por el seed):

- **Planes** — `nombre`, `nivel`
- **Asegurados** — `cedula` (title), `nombre`, `fecha_nacimiento`, `poliza` →Polizas
- **Polizas** — `numero` (title), `titular`→Asegurados, `plan`→Planes, `fecha_alta`, `estado`
- **Coberturas** — `id` (title), `plan`→Planes, `codigo_cpt`, `cubierto`, `dias_carencia`, `documentos_requeridos`
- **Informes_Medicos** — `id_informe` (title), `paciente`→Asegurados, `procedimiento_cpt`, `documentos_adjuntos`, etc.
- **Decisiones** — `id_decision` (title), `informe`→Informes, `decision`, `justificacion`, `clausula_aplicada`, `documentos_faltantes`, `timestamp`
