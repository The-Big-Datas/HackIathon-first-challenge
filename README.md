# Insurance Pre-Authorization Agent

Agente de IA construido con **FastAPI** + **Claude Agent SDK** que reduce a segundos
el tiempo de pre-autorización de cirugías. Recibe el `report_id` de un informe médico
digital (Hospital) y el `patient_id` con su póliza (Aseguradora) — ambos almacenados
en bases de datos de **Notion** — y emite una decisión instantánea: *pre-aprobado*,
*solicitud de documentos faltantes*, *rechazado* o *requiere revisión humana*.

## Arquitectura

```
POST /authorize
      |
      v
PreAuthorizationAgent (Claude Agent SDK)
      |
      +-- tool: fetch_medical_report  --> Notion (Medical Reports DB)
      +-- tool: fetch_policy          --> Notion (Policies DB)
      +-- tool: submit_decision       --> Notion (Decisions DB)
```

El agente recorre un procedimiento determinista guiado por su `system_prompt`:
vigencia → cobertura → carencia → documentos faltantes → decisión.

## Estructura

```
app/
├── main.py                    # FastAPI app
├── config.py                  # Variables de entorno
├── models/schemas.py          # Pydantic schemas
├── routers/authorization.py   # Endpoint POST /authorize
└── services/
    ├── notion_service.py      # CRUD en Notion
    └── agent_service.py       # Claude Agent SDK + tools
```

## Setup

### 1. Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de entorno

Copia `.env.example` a `.env` y llena las claves:

```bash
cp .env.example .env
```

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | API key de Anthropic |
| `NOTION_API_KEY` | Integration secret de Notion |
| `NOTION_MEDICAL_REPORTS_DB_ID` | ID de la base de informes médicos |
| `NOTION_POLICIES_DB_ID` | ID de la base de pólizas |
| `NOTION_DECISIONS_DB_ID` | (opcional) Base donde se guardan las decisiones |

### 3. Estructura recomendada de las bases en Notion

**Medical Reports**

| Propiedad | Tipo |
|---|---|
| `report_id` | Title |
| `patient_id` | Rich text |
| `patient_name` | Rich text |
| `diagnosis` | Rich text |
| `procedure_code` | Rich text |
| `procedure_name` | Rich text |
| `requested_date` | Date |
| `attending_physician` | Rich text |
| `clinical_notes` | Rich text |
| `attachments` | Files & media |

**Policies**

| Propiedad | Tipo |
|---|---|
| `policy_id` | Title |
| `patient_id` | Rich text |
| `plan_name` | Rich text |
| `effective_date` | Date |
| `expiration_date` | Date |
| `covered_procedures` | Multi-select (códigos o nombres) |
| `excluded_procedures` | Multi-select |
| `waiting_periods_months` | Rich text — formato `CIRUGIA:6,ONCOLOGIA:12` |
| `deductible` | Number |
| `coverage_percentage` | Number |
| `status` | Select (`active`, `suspended`, `expired`) |

**Decisions** *(opcional)*

| Propiedad | Tipo |
|---|---|
| `report_id` | Title |
| `patient_id` | Rich text |
| `decision` | Select (`pre_approved`, `missing_documents`, `rejected`, `needs_review`) |
| `rationale` | Rich text |
| `missing_documents` | Multi-select |
| `issued_at` | Date |

Comparte cada base con tu integración de Notion (`Connections` → tu integración).

### 4. Ejecutar

```bash
uvicorn app.main:app --reload
```

Abre http://localhost:8000/docs para explorar el Swagger UI.

## Uso

### curl

```bash
curl -X POST http://localhost:8000/authorize \
  -H "Content-Type: application/json" \
  -d @samples/authorize_request.json
```

### PyCharm / VS Code REST Client

Abre `samples/authorize.http` y ejecuta cualquier petición con el botón **▶**
junto a cada bloque `###`. Incluye 5 escenarios:
- pre-aprobado
- documentos faltantes
- carencia incumplida
- procedimiento excluido
- paciente inexistente

### Datos de prueba

`samples/notion_seed_data.md` describe los registros que debes crear en tus
bases de Notion para reproducir los escenarios anteriores.

Respuesta esperada:

```json
{
  "report_id": "RPT-001",
  "patient_id": "PAT-123",
  "decision": "pre_approved",
  "rationale": "Procedimiento APE001 (Apendicectomía) cubierto por la póliza Premium Plus. Carencia de 6 meses cumplida (póliza vigente desde 2024-01-01). Cobertura 80%.",
  "missing_documents": [],
  "coverage_percentage": 80.0,
  "estimated_patient_cost": 350.0,
  "issued_at": "2026-05-06T18:30:00Z"
}
```
