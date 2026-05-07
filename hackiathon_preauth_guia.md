# Agente de Pre-Autorización Quirúrgica

hacklAthon Viamatica · Reto 1 · Guía de Implementación

Documento de trabajo

Mayo 2026

Pre-Autorización Quirúrgica - hacklAthon

# Resumen ejecutivo

Reto 1 del filtro de ingreso al hackIAthon: construir un agente que reciba un informe médico y la póliza del paciente desde Notion, y emita una pre-autorización quirúrgica (Aprobado / Negado / Documentos faltantes) en segundos.

Stack elegido: FastAPI (backend) + Streamlit (frontend) + Claude (Sonnet 4.6) con tool use directo + Notion como source of truth.

Tiempo objetivo: 4–6 horas, 1–2 personas. Esto es un filtro previo, no la final — guardamos pólvora.

## Diferenciadores clave:

- Arquitectura neuro-simbólica: Claude razona y orquesta, las decisiones críticas (carencia, exclusión, documentos) viven en código Python determinístico.
- Notion como fuente real de datos, no mock.
- Trace del agente visible en la UI.
- Tres casos demo precargados que cubren los tres veredictos posibles.

Pre-Autorización Quirúrgica - hacklAthon

# Estructura del proyecto

```txt
hackiathon-preauth/
├── backend/
|   ├── main.py
|   ├── agent.py
|   ├── tools.py
|   ├── notion_client.py
|   ├── models.py
|   └── prompts.py
|   └── requirements.txt
|   └── .env.example
├── frontend/
|   └── app.py
|   └── requirements.txt
|   └── .streamlit/
└── secrets.toml.example
├── seed/
|   └── populate_notion.py
├── docs/
|   └── notion_setup.md
├── README.md
├── .gitignore
└── LICENSE
```

```txt
.gitignore:
```

```txt
.env
**/secrets.toml**
__pycache__/
*.pyc
.venv/
.DS_Store
```

3 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Requirements y variables de entorno

## backend/requirements.txt :

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
anthropic==0.39.0
notion-client==2.2.1
pydantic==2.9.2
python-dotenv==1.0.1
```

## frontend/requirements.txt :

```txt
streamlit==1.39.0
requests==2.32.3
```

## backend/.env.example :

```txt
ANTHROPIC_API_KEY=sk-ant-...
NOTION_TOKEN=ntn...
NOTION_DB_ASEGURADOS=
NOTION_DB_POLIZAS=
NOTION_DB_PLANES=
NOTION_DB_COBERTURAS=
NOTION_DB_INFORMES=
NOTION_DB_DECISIONES=
CLAUDE_MODEL=claude-sonnet-4-6
```

## frontend/.streamlit/secrets.toml.example :

```batch
BACKEND_URL = "https://tu-backend.onrender.com"
```

4 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Setup de Notion

## Crear la integración

1. Entrar a https://www.notion.so/profile/integrations, crear Internal Integration, nombre "HacklAthon PreAuth".
2. Copiar el Internal Integration Token (empieza con ntn_). Va en NOTION_TOKEN.
3. En el workspace, crear página padre "HacklAthon PreAuth". Click en *** → + Add Connections → seleccionar la integración. Crítico: si no se conecta la página, la API tira 404.

## Crear las 6 databases

Crear cada DB con /Database - Full page dentro de la página padre. Los nombres de los campos son case-sensitive — respetarlos exactamente.

### Asegurados

|  Property | Tipo  |
| --- | --- |
|  cedula | Title  |
|  nombre | Rich text  |
|  fecha_nacimiento | Date  |
|  poliza | Relation → Polizas  |

### Planes

|  Property | Tipo  |
| --- | --- |
|  nombre | Title  |
|  nivel | Select (Basico, Estandar, Premium)  |

Pre-Autorización Quirúrgica hacklAthon

# Polizas

|  Property | Tipo  |
| --- | --- |
|  numero | Title  |
|  titular | Relation → Asegurados  |
|  plan | Relation → Planes  |
|  fecha_alta | Date  |
|  estado | Select (Vigente, Suspendida, Cancelada, Vencida)  |

# Coberturas

|  Property | Tipo  |
| --- | --- |
|  id | Title  |
|  plan | Relation → Planes  |
|  codigo_cpt | Rich text  |
|  descripcion | Rich text  |
|  cubierto | Checkbox  |
|  dias_carencia | Number  |
|  documentos_requeridos | Multi-select (informe_quirurgico, examenes_prequirurgicos,segundo_dictamen, exames_imagen,consentimiento)  |

# Informes_Medicos

|  Property | Tipo  |
| --- | --- |
|  id_informe | Title  |
|  paciente | Relation → Asegurados  |
|  fecha_emision | Date  |
|  hospital | Rich text  |
|  medico_tratante | Rich text  |
|  diagnostico_cie10 | Rich text  |
|  procedimiento_cpt | Rich text  |
|  descripcion_procedimiento | Rich text  |
|  justificacion_clinica | Rich text  |
|  fecha_programada | Date  |
|  documentos_adjuntos | Multi-select (mismas opciones que documentos_requeridos)  |

Pre-Autorización Quirúrgica - hacklAthon

## Decisiones

|  Property | Tipo  |
| --- | --- |
|  id_decision | Title  |
|  informe | Relation → Informes_Medicos  |
|  decision | Select (Aprobado, Negado, Documentos_Faltantes)  |
|  justificacion | Rich text  |
|  clausula_aplicada | Rich text  |
|  documentos_faltantes | Multi-select (mismas opciones)  |
|  timestamp | Date  |

## Conseguir los IDs de cada DB

Abrir cada DB en navegador. La URL es:

https://www.notion.so/<workspace>/<database_id>?v=...

El DATABASE_ID son los 32 caracteres antes del ? . Copiar cada uno al .env .

## Sembrar datos demo

seed/populate_notion.py :</database_id>

Pre-Autorización Quirúrgica - hackIAthon

```python
&gt;&gt;&gt; Siembra datos demo en Notion. Correr UNA vez después de crear las DBs.
&gt; Asume que las 6 DBs existen vacías y que sus IDs están en backend/.env
&gt;&gt;&gt; import os
&gt; from datetime import date, timedelta
&gt; from dotenv import load_dotenv
&gt; from notion_client import Client
&gt;
&gt; load_dotenv("../backend/.env")
&gt; notion = Client(auth=os.environ["NOTION_TOKEN"])
&gt;
&gt; DB = {
&gt; "asegurados": os.environ["NOTION_DB_ASEGURADOS"],
&gt; "polizas": os.environ["NOTION_DB_POLIZAS"],
&gt; "planes": os.environ["NOTION_DB_PLANES"],
&gt; "coberturas": os.environ["NOTION_DB_COBERTURAS"],
&gt; "informes": os.environ["NOTION_DB_INFORMES"],
}
&gt;
&gt; HOY = date.today()
&gt;
&gt;
&gt; # --- 1. Planes ---
&gt; def crear_plan(nombre, nivel):
&gt; r = notion.pages.create(
&gt;     parent={"database_id": DB["planes"]},
&gt;     properties={
&gt;     "nombre": {"title": [{"text": {"content": nombre}}]},
&gt;     "nivel": {"select": {"name": nivel}},
&gt;     },
&gt;     )
&gt;     return r["id"]
&gt;
&gt; plan_basico = crear_plan("Plan Salud Basico", "Basico")
&gt; plan_estandar = crear_plan("Plan Salud Estandar", "Estandar")
&gt; plan_premium = crear_plan("Plan Salud Premium", "Premium")
&gt;
&gt; print(f"Planes: basico={plan_basico} estandar={plan_estandar} premium={plan_premium}")
&gt;
&gt; # --- 2. Coberturas ---
&gt; def crear_cobertura(plan_id, cpt, desc, cubierto, dias_carencia, docs_req):
&gt; notion.pages.create(
&gt;     parent={"database_id": DB["coberturas"]},
&gt;     properties={
&gt;     "id": {"title": [{"text": {"content": f"COB-{cpt}-{plan_id[:4]}"}}]},
&gt;     "plan": {"relation": [{"id": plan_id}]},
&gt;     "codigo_cpt": {"rich_text": [{"text": {"content": cpt}}]},
&gt;     "descripcion": {"rich_text": [{"text": {"content": desc}}]},
&gt;     "cubierto": {"checkbox": cubierto},
&gt;     "dias_carencia": {"number": dias_carencia},
&gt;     "documentos_requeridos": {
&gt;     "multi_select": [{"name": d} for d in docs_req]},
&gt; },
&gt; },
&gt; }
&gt;
&gt; # Apendicectomia (44970) - cubierta en todos los planes
&gt; crear_cobertura(plan_basico, "44970", "Apendicectomia laparoscopica", True, 90,

Pre-Autorización Quirúrgica - hacklAthon

```r
["informe_quirurgico", "examenes_prequirurgicos"])
crear_cobertura(plan_estandar, "44970", "Apendicectomia laparoscopica", True, 60,
["informe_quirurgico", "examenes_prequirurgicos"])
crear_cobertura(plan_premium, "44970", "Apendicectomia laparoscopica", True, 30,
["informe_quirurgico"])

# Colecistectomia (47562) - cubierta, requiere mas docs
crear_cobertura(plan_estandar, "47562", "Colecistectomia laparoscopica", True, 90,
["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"])
crear_cobertura(plan_premium, "47562", "Colecistectomia laparoscopica", True, 30,
["informe_quirurgico", "examenes_prequirurgicos"])

# Cirugía bariatrica (43644) - solo planes altos, carencia larga
crear_cobertura(plan_estandar, "43644", "Cirugía bariatrica - bypass gastrico", True, 365,
["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen",
"exames_imagen"])

crear_cobertura(plan_premium, "43644", "Cirugía bariatrica - bypass gastrico", True, 180,
["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"]
crear_cobertura(plan_basico, "43644", "Cirugía bariatrica - bypass gastrico", False, 0,
[])

print("Coberturas creadas")

# --- 3. Asegurados + Polizas ---
def crear_asegurado(cedula, nombre, fnac):
r = notion.pages.create(
parent={"database_id": DB["asegurados"]},
properties={
"cedula": {"title": ["text": {"content": cedula}]}],
"nombre": {"rich_text": ["text": {"content": nombre}]}],
"fecha_nacimiento": {"date": {"start": fnac.isoformat()}},
},
)
return r["id"]

def crear_poliza(numero, titular_id, plan_id, fecha_alta, estado):
r = notion.pages.create(
parent={"database_id": DB["polizas"]},
properties={
"numero": {"title": ["text": {"content": numero}]}],
"titular": {"relation": ["id": titular_id]}],
"plan": {"relation": ["id": plan_id]}],
"fecha_alta": {"date": {"start": fecha_alta.isoformat()}},
"estado": {"select": {"name": estado}},
},
)
notion.pages.update(
titular_id,
properties={"poliza": {"relation": ["id": r["id"]}]},
)
return r["id"]

# Caso A: Premium, poliza vigente hace 2 anios -&gt; aprobacion limpia
a1 = crear_asegurado("0912345678", "Juan Perez Andrade", date(1985, 5, 12))
crear_poliza("POL-001", a1, plan_premium, HOY - timedelta(days=730), "Vigente")

# Caso B: Estandar, poliza vigente hace 45 días -&gt; rechazo por carencia
a2 = crear_asegurado("0923456789", "Maria Gonzalez Vera", date(1978, 9, 3))
crear_poliza("POL-002", a2, plan_estandar, HOY - timedelta(days=45), "Vigente")
```

9 / 40

Pre-Autorización Quirúrgica - hacklAthon

```python
# Caso C: Estandar, poliza vigente hace 1 anio -&gt; docs faltantes
a3 = crear_asegurado("0934567890", "Carlos Bermeo Loja", date(1990, 1, 22))
crear_poliza("POL-003", a3, plan_estandar, HOY - timedelta(days=365), "Vigente")
print("Asegurados y polizas creados")
```

```python
# --- 4. Informes Medicos ---
def crear_informe(id_inf, paciente_id, hospital, medico, cie10, cpt, desc, justif, dias_futuro, docs):
notion.pages.create(
parent={"database_id": DB["informes"]},
properties={
"id_informe": {"title": [{"text": {"content": id_inf}}}]},
"paciente": {"relation": [{"id": paciente_id}]}],
"fecha_emision": {"date": {"start": HOY.isoformat()}}],
"hospital": {"rich_text": [{"text": {"content": hospital}}}]},
"medico_tratante": {"rich_text": [{"text": {"content": medico}}}]},
"diagnostico_cie10": {"rich_text": [{"text": {"content": cie10}}}]},
"procedimiento_cpt": {"rich_text": [{"text": {"content": cpt}}}]},
"descripcion_procedimiento": {"rich_text": [{"text": {"content": desc}}}]},
"justificacion_clinica": {"rich_text": [{"text": {"content": justif}}}]},
"fecha_programada": {
"date": {"start": (HOY + timedelta(days=dias_futuro)).isoformat()}}
},
"documentos_adjuntos": {
"multi_select": [{"name": d} for d in docs]}
}
}
}
}
```

```python
crear_informe(
"INF-001", a1, "Hospital Metropolitano", "Dr. Velasquez",
"K35.9", "44970", "Apendicectomia laparoscopica",
"Paciente con dolor abdominal en fosa iliaca derecha, leucocitosis, "
"ecografia confirma apendicitis aguda. Indicacion quirurgica urgente.",
2, ["informe_quirurgico", "examenes_prequirurgicos"]
)
```

```python
crear_informe(
"INF-002", a2, "Hospital Vozandes", "Dra. Mora",
"E66.01", "43644", "Cirugía bariatrica - bypass gastrico",
"Paciente con IMC 41, comorbilidades metabólicas, falla terapia "
"conservadora 18 meses. Candidata a manejo quirúrgico.",
14, ["informe_quirúrgico", "examenes_prequirúrgicos", "segundo_dictamen"]
)
```

```python
crear_informe(
"INF-003", a3, "Hospital Alcivar", "Dr. Mendoza",
"K80.20", "47562", "Colecistectomia laparoscopica",
"Paciente con colelitiasis sintomática, episodios de colico biliar "
"recurrentes, ecografía con cálculo de 2cm. Indicación quirúrgica electiva.",
7, ["informe_quirúrgico"]
)
```

```python
print("Informes médicos creados. Listo para procesar.")

Pre-Autorización Quirúrgica - hacklAthon

Correr python seed/populate_notion.py desde el directorio seed/.

11 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Schemas Pydantic

backend/models.py :

Pre-Autorización Quirúrgica - hacklAthon

```python
from datetime import date
from pydantic import BaseModel
from typing import Literal, Optional

class Plan(BaseModel):
id: str
nombre: str
nivel: Literal["Basico", "Estandar", "Premium"]

class Asegurado(BaseModel):
id: str
cedula: str
nombre: str
fecha_nacimiento: Optional[date]
poliza_id: Optional[str]

class Poliza(BaseModel):
id: str
numero: str
titular_cedula: str
plan_id: str
plan_nombre: str
fecha_alta: date
estado: Literal["Vigente", "Suspendida", "Cancelada", "Vencida"]

class Cobertura(BaseModel):
id: str
plan_id: str
codigo_cpt: str
descripción: str
cubierto: bool
días_carencia: int
documentos_requeridos: list[str]

class InformeMedico(BaseModel):
id: str
id_informe: str
paciente_cedula: str
fecha_emision: date
hospital: str
medico_tratante: str
diagnostico_cie10: str
procedimiento_cpt: str
descripción_procedimiento: str
justificación_clínica: str
fecha_programada: date
documentos_adjuntos: list[str]

class DecisionPayload(BaseModel):
informe_id: str
decisión: Literal["Aprobado", "Negado", "Documentos_Faltantes"]
justificación: str

Pre-Autorización Quirúrgica - hackIAthon

```txt
clausula_aplicada: str
documentos_faltantes: list[str] = []

Pre-Autorización Quirúrgica - hacklAthon

# Cliente Notion

backend/notion_client.py:

15 / 40

Pre-Autorización Quirúrgica - hacklAthon

```python
import os
from datetime import datetime, date
from notion_client import Client
from dotenv import load_dotenv

from models import (
Plan, Asegurado, Poliza, Cobertura, InformeMedico, DecisionPayload
)

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

DB_ASEGURADOS = os.environ["NOTION_DB_ASEGURADOS"]
DB_POLIZAS = os.environ["NOTION_DB_POLIZAS"]
DB_PLANES = os.environ["NOTION_DB_PLANES"]
DB_COBERTURAS = os.environ["NOTION_DB_COBERTURAS"]
DB_INFORMES = os.environ["NOTION_DB_INFORMES"]
DB_DECISIONES = os.environ["NOTION_DB_DECISIONES"]
```

```python
# --- Helpers para extraer properties ---
def _title(p):
return p["title"][0]["plain_text"] if p.get("title") else ""
def _rich(p):
return p["rich_text"][0]["plain_text"] if p.get("rich_text") else ""
def _select(p):
return p["select"]["name"] if p.get("select") else None
def _multi(p):
return [o["name"] for o in p.get("multi_select", [])]
def _checkbox(p):
return p.get("checkbox", False)
def _number(p):
return p.get("number")
def _date(p):
d = p.get("date")
if not d or not d.get("start"):
return None
return date.fromisoformat(d["start"][:10])
def _relation_first(p):
rels = p.get("relation", [])
return rels[0]["id"] if rels else None
```

```python
# --- Lecturas ---
def get_asegurado_by_cedula(cedula: str) -&gt; Asegurado | None:
r = notion.databases.query(database_id=DB_ASEGURADOS, filter={"property": "cedula", "title": {"equals": cedula}}, ) if not r["results"];

Pre-Autorización Quirúrgica - hacklAthon

```vhdl
return None
page = r["results"][0]
props = page["properties"]
return Asegurado(
id=page["id"],
cedula=_title(props["cedula"]),
nombre=_rich(props["nombre"]),
fecha_nacimiento=_date(props["fecha_nacimiento"]),
poliza_id=_relation_first(props["poliza"]),
)

def get_poliza(poliza_id: str) -&gt; Poliza | None:
page = notion.pages.retrieve(poliza_id)
props = page["properties"]
plan_id = _relation_first(props["plan"])
titular_id = _relation_first(props["titular"])
if not plan_id or not titular_id:
return None
plan = get_plan(plan_id)
titular = notion.pages.retrieve(titular_id)
return Poliza(
id=page["id"],
numero=_title(props["numero"]),
titular_cedula=_title(titular["properties"]["cedula"]),
plan_id=plan_id,
plan_nombre=plan.nombre if plan else "",
fecha_alta=_date(props["fecha_alta"]),
estado=_select(props["estado"]),
)

def get_plan(plan_id: str) -&gt; Plan | None:
page = notion.pages.retrieve(plan_id)
props = page["properties"]
return Plan(
id=page["id"],
nombre=_title(props["nombre"]),
nivel=_select(props["nivel"]),
)

def get_cobertura(plan_id: str, codigo_cpt: str) -&gt; Cobertura | None:
r = notion.databases.query(
database_id=DB_COBERTURAS,
filter={
"and": [
{"property": "plan", "relation": {"contains": plan_id}},
{"property": "codigo_cpt", "rich_text": {"equals": codigo_cpt}},
]
},
)
if not r["results"];
return None
page = r["results"][0]
props = page["properties"]
return Cobertura(
id=page["id"],
plan_id=plan_id,
```

17 / 40

Pre-Autorización Quirúrgica - hacklAthon

```r
codigo_cpt=_rich(props["codigo_cpt"]),
descripcion=_rich(props["descripcion"]),
cubierto=_checkbox(props["cubierto"]),
dias_carencia=int(_number(props["dias_carencia"]) or 0),
documentos_requeridos=_multi(props["documentos_requeridos"]),
)

def get_informe(informe_id_legible: str) -&gt; InformeMedico | None:
r = notion.databases.query(
database_id=DB_INFORMES,
filter={"property": "id_informe", "title": {"equals": informe_id_legible}}),
)
if not r["results"];
return None
page = r["results"][0]
props = page["properties"]
paciente_id = _relation_first(props["paciente"])
paciente = notion.pages.retrieve(paciente_id) if paciente_id else None
return InformeMedico(
id=page["id"],
id_informe=_title(props["id_informe"]),
paciente_cedula=_title(paciente["properties"]["cedula"]) if paciente else "", fecha_emision=_date(props["fecha_emision"]),
hospital=_rich(props["hospital"]),
medico_tratante=_rich(props["medico_tratante"]),
diagnostico_cie10=_rich(props["diagnostico_cie10"]),
procedimiento_cpt=_rich(props["procedimiento_cpt"]),
descripcion_procedimiento=_rich(props["descripcion_procedimiento"]),
justificacion_clinica=_rich(props["justificacion_clinica"]),
fecha_programada=_date(props["fecha_programada"]),
documentos_adjuntos=_multi(props["documentos_adjuntos"]),
)

def list_informes() -&gt; list[dict]:
r = notion.databases.query(database_id=DB_INFORMES, page_size=20)
out = []
for page in r["results"];
props = page["properties"]
out.append({
"id_informe": _title(props["id_informe"]),
"descripcion_procedimiento": _rich(props["descripcion_procedimiento"]),
"hospital": _rich(props["hospital"]),
})
return out
```

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

```r
def crear_decision(payload: DecisionPayload) -&gt; str:
informe = get_informe(payload.informe_id)
if not informe:
raise ValueError(f"Informe {payload.informe_id} no existe")
suffix = datetime.now().strftime("%H%M%S")
r = notion.pages.create(
parent={"database_id": DB_DECISIONES},
properties={
"id_decision": {
"title": [{"text": {"content": f"DEC-{payload.informe_id}-{suffix}"}}]
}
}
}
```

18 / 40

Pre-Autorización Quirúrgica - hackIAthon

```javascript
},
"informe": {"relation": ["id": informe.id}]},
"decision": {"select": {"name": payload.decision}}},
"justificacion": {
"rich_text": ["text": {"content": payload.justificacion[:1900]]}]
},
"clausula_aplicada": {
"rich_text": ["text": {"content": payload.clausula_aplicada[:200]]}]
},
"documentos_faltantes": {
"multi_select": ["name": d} for d in payload.documentos_faltantes]
},
"timestamp": {"date": {"start": datetime.now().isoformat()}},
},
}
return r["id"]
```

19 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Tools y policy engine

backend/tools.py:

20 / 40

Pre-Autorización Quirúrgica - hackIAthon

```python
from datetime import date
import notion_client as nc
from models import DecisionPayload

# ============== Definiciones de tools para Claude ==============
TOOL_DEFINITIONS = [
{
"name": "get_informe_medico",
"description": "Obtiene el informe medico completo desde Notion. Siempre se llama PRIMERO.",
"input_schema": {
"type": "object",
"properties": {
"informe_id": {
"type": "string",
"description": "Identificador legible del informe (ej. INF-001)"
}
},
"required": ["informe_id"],
},
},
{
"name": "get_poliza_paciente",
"description": "Obtiene la poliza vigente del paciente a partir de su cedula. Si no existe, retorna error.",
"input_schema": {
"type": "object",
"properties": {"cedula": {"type": "string"}},
"required": ["cedula"],
},
},
{
"name": "get_cobertura",
"description": "Obtiene la regla de cobertura para un procedimiento bajo un plan. Devuelve si esta cubierto, días de carencia, y documentos requeridos.",
"input_schema": {
"type": "object",
"properties": {
"plan_id": {"type": "string"}},
"codigo_cpt": {"type": "string"}
},
"required": ["plan_id", "codigo_cpt"]
},
},
{
"name": "verificar_carencia",
"description": "Determina si la poliza cumple el periodo de carencia exigido. Calculo deterministico, NO debe ser hecho por el LLM.",
"input_schema": {
"type": "object",
"properties": {
"fecha_alta_poliza": {"type": "string", "description": "ISO date YYYY-MM-DD"},
"fecha_evento": {"type": "string", "description": "ISO date YYYY-MM-DD"},
"días_carencia_requeridos": {"type": "integer"}
}
```

21 / 40

Pre-Autorización Quirúrgica - hacklAthon

```json
"required": ["fecha_alta_poliza", "fecha_evento", "dias_carencia_requeridos"], }
},
{
"name": "validar_documentos",
"description": "Compara documentos requeridos vs adjuntos. Devuelve la lista de faltantes.",
"input_schema": {
"type": "object",
"properties": {
"documentos_requeridos": {"type": "array", "items": {"type": "string"}},
"documentos_adjuntos": {"type": "array", "items": {"type": "string"}},
"required": ["documentos_requeridos", "documentos_adjuntos"], }
},
{
"name": "emitir_decision",
"description": "Escribe la decision final en Notion. Es la ULTIMA tool que se llama.",
"input_schema": {
"type": "object",
"properties": {
"informe_id": {"type": "string"}},
"decision": {
"type": "string",
"enum": ["Aprobado", "Negado", "Documentos_Faltantes"]
},
"justificacion": {
"type": "string",
"description": "Texto en espanol claro, entendible por un paciente"
},
"clausula_aplicada": {
"type": "string",
"description": "Referencia a la regla que sustenta la decision"
},
"documentos_faltantes": {"type": "array", "items": {"type": "string"}},
"required": ["informe_id", "decision", "justificacion", "clausula_aplicada"], }
},
}
]
```

# =============== Implementaciones ============
```python
def _get_informe_medico(informe_id: str) -&gt; dict:
inf = nc.get_informe(informe_id)
if not inf:
return {"error": f"Informe {informe_id} no encontrado"}
return inf.model_dump(mode="json")
```

```python
def _get_poliza_paciente(cedula: str) -&gt; dict:
asegurado = nc.get_asegurado_by_cedula(cedula)
if not asegurado:
return {"error": f"No existe asegurado con cedula {cedula}"}
if not asegurado.poliza_id:
return {"error": f"Asegurado {cedula} no tiene poliza asociada"}
poliza = nc.get_poliza(asegurado.poliza_id)
```

22 / 40

Pre-Autorización Quirúrgica - hacklAthon

```r
if not poliza:
return {"error": "Poliza no encontrada"}
return poliza.model_dump(mode="json")
def _get_cobertura(plan_id: str, codigo_cpt: str) -&gt; dict:
cob = nc.get_cobertura(plan_id, codigo_cpt)
if not cob:
return {
"cubierto": False,
"motivo": (
f "No existe regla de cobertura para CPT {codigo_cpt} bajo "
"el plan indicado. Procedimiento NO incluido."
)
}
return cob.model_dump(mode="json")
def _verificar_carencia(fecha_alta_poliza: str, fecha_evento: str,
dias_carencia_requeridos: int) -&gt; dict:
fa = date.fromisoformat(fecha_alta_poliza)
fe = date.fromisoformat(fecha_evento)
transcurridos = (fe - fa).days
cumple = transcurridos &gt;= dias_carencia_requeridos
return {
"cumple": cumple,
"dias_transcurridos": transcurridos,
"dias_requeridos": dias_carencia_requeridos,
"dias_faltantes": max(0, dias_carencia_requeridos - transcurridos),
}
def _validar_documentos(documentos_requeridos: list[str],
documentos_adjuntos: list[str]) -&gt; dict:
req = set(documentos_requeridos)
adj = set(documentos_adjuntos)
faltantes = sorted(req - adj)
return {
"completo": len(faltantes) == 0,
"documentos_faltantes": faltantes,
}
def _emitir_decision(informe_id: str, decision: str, justificacion: str,
clausula_aplicada: str,
documentos_faltantes: list[str] = None) -&gt; dict:
payload = DecisionPayload(
informe_id=informe_id,
decision=decision,
justificacion=justificacion,
clausula_aplicada=clausula_aplicada,
documentos_faltantes=documentos_faltantes or [],
)
decision_id = nc.crear_decision(payload)
return {"ok": True, "decision_id": decision_id, "decision": decision}
```

```txt
# Dispatcher
def execute_tool(name: str, payload: dict) -&gt; dict:

Pre-Autorización Quirúrgica - hackIAthon

```txt
handlers = {
"get_informe_medico": _get_informe_medico,
"get_poliza_paciente": _get_poliza_paciente,
"get_cobertura": _get_cobertura,
"verificar_carencia": _verificar_carencia,
"validar_documentos": _validar_documentos,
"emitir_decision": _emitir_decision,
}
if name not in handlers:
return {"error": f"Tool {name} no existe"}
try:
return handlers[name] (**payload)
except Exception as e:
return {"error": f"{type(e),__name__}: {e}"
}
```

24 / 40

Pre-Autorización Quirúrgica - hacklAthon

# System prompt

# backend/prompts.py :

```txt
SYSTEM_prompt = ""Eres un agente de pre-autorizacion de cirugias para una aseguradora de
salud en Ecuador. Tu trabajo es analizar informes medicos y emitir una de tres decisiones:
Aprobado, Negado, o Documentos_Faltantes.
```

```txt
PROCESO OBLIGATORIO (en esteorden):
```

1. Lee el informe medico completo con get_informe_medico.
2. Obten la poliza del paciente con get_poliza_paciente usando la cedula del informe.
- Si la poliza no esta Vigente -&gt; Negado citando el estado de la poliza.
3. Obten la regla de cobertura con get_cobertura usingo el plan_id de la poliza y el
codigo_cpt del procedimiento.
- Si no existe regla o cubierto=false -&gt; Negado citando exclusion de cobertura.
4. Verifica la carencia con verificar_carencia usingo fecha_alta de la poliza,
fecha_programada del procedimiento, y dias_carencia de la cobertura.
- Si cumple=false -&gt; Negado citando el periodo de carencia.
5. Valida los documentos adjuntos con validar_documentos usingo documentos_requeridos de la
cobertura y documentos_adjuntos del informe.
- Si completo=false -&gt; Documentos_Faltantes con la lista exacta.
6. Si todos los chequeos pasan -&gt; Aprobado.
7. SIEMPRE termina llamando emitir_decision con la decision final.

# REGLAS DURAS:

- NUNCA inventes datos de la poliza, cobertura o carencia. Siempre consultals via tools.
- NUNCA decidas en tu cabeza si una carencia se cumple - usa verificar_carencia.
- La justificacion debe ser clara, en espanol, entendible por un paciente, citando datos
concretos.
- Cita siempre la regla aplicada como clausula_aplicada.
- Detente apenas tengas suficiente informacion para una decision negativa.

# FORMATO DE JUSTIFICACION (ejemplos):

- Aprobado: "Se aprueba la pre-autorizacion para [procedimiento] (CPT [codigo]). Poliza
vigente desde [fecha], cumple carencia de X dias requeridos. Todos los documentos
requeridos estan adjuntos."
- Negado por carencia: "Se niega la pre-autorizacion. La poliza tiene X dias desde su alta,
el procedimiento [nombre] requiere un periodo de carencia de Y dias. Aprobacion possible a
partir de [fecha calculable]."
- Documentos faltantes: "Para procesar la pre-autorizacion del [procedimiento], se
requieren los siguientes documentos adiconiales: [lista]. Una vez completados, reenviar el
caso."

Siempre responde con texto final breve resumiendo la decision para el usuario, despues de
llamar emitir_decision."

Pre-Autorización Quirúrgica - hacklAthon

# Agent loop

backend/agent.py :

Pre-Autorización Quirúrgica - hacklAthon

```python
import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

from tools import TOOL_DEFINITIONS, execute_tool
from prompts import SYSTEM_prompt

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

def run_agent(informe_id: str) -&gt; dict:
"--
Ejecuta el loop agentico para procesar un informe.
Retorna {trace, final_text, decision}:
- trace: lista de {tool, input, output} en orden de ejecucion
- final_text: respuesta final del agente
- decision: dict con la decision emitida (o None)
"--
messages = [
"role": "user",
"content": f"Procesa la pre-autorizacion del informe {informe_id}."
}]
trace = []
decision_emitida = None

for _ in range(15): # safety net
response = client.messages.create(
model=MODEL,
max_tokens=4096,
system=SYSTEM_prompt,
tools=TOOL_DEFINITIONS,
messages=messages,
)

if response.stop_reason == "end_turn":
final_text = "\n".join(
b.text for b in response.content if b.type == "text"
)
return {
"trace": trace,
"final_text": final_text,
"decision": decision_emitida,
}

if response.stop_reason == "tool_use":
tool_results = []
for block in response.content:
if block.type == "tool_use":
result = execute_tool(block.name, block.input)
if block.name == "emitir_decision" and result.get("ok"):
decision_emitida = {
"decision": block.input.get("decision"),
"justificacion": block.input.get("justificacion"),
"clausula_aplicada": block.input.get("clausula_aplicada"),
}
}
```

27 / 40

Pre-Autorización Quirúrgica - hackIAthon

```txt
"documentos_faltantes": block.input.get(
"documentos_faltantes", []
),
)
trace.append({
"tool": block.name,
"input": block.input,
"output": result,
})
tool_results.append({
"type": "tool_result",
"tool_use_id": block.id,
"content": json.dumps(result, default=str, ensure_ascii=False),
})
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": tool_results})
else:
break
```

raise RuntimeError("Agente alcanzo limite de iteraciones. Trace: {trace}")
```

28 / 40

Pre-Autorización Quirúrgica - hacklAthon

# FastAPI backend

```python
backend/main.py:
```

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agent import run_agent
import notion_client as nc
```

```python
app = FastAPI(title="Agente Pre-Autorizacion Quirurgica")
```

```python
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_methods=["*"],
allow_headers=["*"],
)
```

```python
@app.get("/health")
def health():
return {"ok": True}

@app.get("/informes")
def listar_informes():
return nc.list_informes()

@app.post("/procesar/{informe_id}")
def procesar(informe_id: str):
try:
return run_agent(informe_id)
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))
```

# Para correr local:

```bash
cd backend &amp;&amp; uvicorn main:app --reload
```

29 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Frontend Streamlit

frontend/app.py :

Pre-Autorización Quirúrgica - hackIAthon

```python
import streamlit as st
import requests

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
page_title="Pre-Autorizacion Quirurgica",
page_icon="中"
layout="wide",
)

st.title("Agente de Pre-Autorizacion Quirurgica")
st.caption("hackIAthon · Reto 1 · Powered by Claude")

@st.cache_data(ttl=60)
def cargar_informes():
r = requests.get(f"{BACKEND_URL}/informes", timeout=20)
r.raise_for_status()
return r.json()

try:
informes = cargar_informes()
except Exception as e:
st.error(f"No se pudo conectar al backend: {e}")
st.stop()

if not informes:
stlearning("No hay informes en Notion. Corre el script de seed primero.")
st.stop()

opciones = {
f"{i['id_informe']} - {i['descripcion_procedimiento']} {i['hospital']}":
i['id_informe']
for i in informes
}

col1, col2 = st.columns([2, 1])
with col1:
seleccion_label = st.selectbox("Selecciona un informe", list(opciones.keys())
with col2:
st.write("")
st.write("")
procesar = st.button(
"Procesar pre-autorizacion",
type="primary",
use_container_width=True,
)

if procesar:
informe_id = opciones[seleccion_label]
with st.spinner(f"El agente esta analizando el informe {informe_id}..."):
try:
r = requests.post(
f"{BACKEND_URL}/procesar/{informe_id}", timeout=120
)
r.raise_for_status()
```

31 / 40

Pre-Autorización Quirúrgica - hacklAthon

```python
data = r.json()
except Exception as e:
st.error(f"Error procesando: {e}")
st.stop()

decision = data.get("decision") or {}
icono_map = {
"Aprobado": "🗑️",
"Negado": "🗝",
"Documentos_Faltantes": "👂",
}
icono = icono_map.get(decision.get("decision"), "?")
st.markdown("---")
st.subheader(f"{icono} Decision: {decision.get('decision', 'Sin decision')}")
if decision.get("decision") == "Aprobado":
st.success(decision.get("justificacion", ""))
elif decision.get("decision") == "Negado":
st.error(decision.get("justificacion", ""))
elif decision.get("decision") == "Documentos_Faltantes":
stlearning(decision.get("justificacion", ""))
if decision.get("documentos_faltantes"):
st.markdown("**Documentos faltantes:**")
for d in decision["documentos_faltantes"]:
st.markdown(f"- {d}")
if decision.get("clausula_aplicada"):
st.caption(f"Clausula aplicada: {decision['clausula_aplicada']}")
st.markdown("---")
with st.expander(f"Trace del agente ({len(data['trace']}) pasos"):
for i, paso in enumerate(data["trace"], 1):
st.markdown(f"### Paso {i}: '{paso['tool']}")
c1, c2 = st.columns(2)
with c1:
st.markdown("**Input**")
st.json(paso["input"])
with c2:
st.markdown("**Output**")
st.json(paso["output"])
st.markdown("---")
if data.get("final_text"):
with st.expander("Respuesta final del agente"):
st.markdown(data["final_text"])
```

Para correr local:

```python
cd frontend &amp;&amp; streamlit run app.py

Pre-Autorización Quirúrgica - hacklAthon

# Deploy

## Backend en Render (free tier)

1. Push del repo a GitHub.
2. En Render: New → Web Service → conectar el repo.
3. Root Directory: backend
4. Build Command: pip install -r requirements.txt
5. Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
6. Variables de entorno: pegar todas las del .env.
7. Anotar la URL pública ( https://xxx.onrender.com ).

Heads up Render free tier: se duerme tras 15 min de inactividad y tarda ~30s en despertar. Antes de mandar el correo, hacer curl https://tu-url/health para despertarlo. Mejor: poner cron-job.org haciendo ping cada 10 min.

## Frontend en Streamlit Community Cloud

1. https://share.streamlit.io → New app → conectar el repo.
2. Main file path: frontend/app.py
3. Advanced settings → Secrets: pegar BACKEND_URL = "https://tu-backend.onrender.com"
4. Deploy. URL queda como https://xxx.streamlit.app. Esa es la que se manda.

## Cuota de Anthropic

Cada procesamiento consume ~5–15k tokens. Con $5 USD aguantan cientos de procesamientos.

Pre-Autorización Quirúrgica - hackIAthon

# README.md

34 / 40

Pre-Autorización Quirúrgica - hackIAthon

# Agente de Pre-Autorización Quirúrgica

Reto 1 del hackIAthon de Viamatica. Sistema agénico que analiza informes médicos y emite pre-autorizaciones de cirugía en segundos en lugar de horas.

# Demo

- App Pública: https://xxx.streamlit.app
- Workspace de Notion (read-only): [opcional]

# Arquitectura

Tres capas:

- **Capa neuronal** - Claude (Sonnet 4.6) con tool use estructurado. Razona, orquesta consultas, redacta justificaciones en español.
- **Capa simbólica** - Policy engine en Python puro. Las decisiones críticas (vigencia, carencia, exclusiones, documentos) son determinísticas.
- **Capa de persistencia y auditoría** - Notion como source of truth. Cada decisión emitida queda registrada con su trace.

```
Streamlit UI -HTTP-&gt; [FastAPI] -tool use-&gt; [Claude] &lt;-tools-&gt; [Notion API]
|  ++&gt; [Policy Engine (Python)]
```

No usamos frameworks de agentes (LangChain, CrewAI, etc.) – SDK directo de Anthropic con tool use, -80 líneas en el loop. Menos magia, más auditableidad.

# Casos demo precargados

| Informe | Caso esperado | Razón |
|---|---|---|
| INF-001 | Aprobado | Plan Premium, póliza de 2 años, apendicectomía con docs completos |
| INF-002 | Negado | Cirugía bariátrica con póliza de 45 días (carencia 365) |
| INF-003 | Docs faltantes | Colecistectomía bajo plan Estándar requiere segundo dictamen |

# Cómo correr local

Requisitos: Python 3.11+, cuenta de Notion, API key de Anthropic.

```
bash
git clone <repo>
cd hackiathon-preauth
```

1. Setup de Notion: crear las 6 DBs siguiendo docs/notion_setup.md
2. Llenar backend/.env con todas las credenciales
3. Sembrar datos demo
cd seed &amp;&amp; python populate_notion.py &amp;&amp; cd ..
4. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
5. Frontend (en otra terminal)</repo>

Pre-Autorización Quirúrgica - hackIAthon

```txt
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

## Stack

- Python 3.11
- Anthropic SDK (Claude Sonnet 4.6)
- FastAPI + Uvicorn
- Streamlit
- Notion API (notion-client)
- Pydantic v2

## Equipo

[nombres]

Pre-Autorización Quirúrgica - hacklAthon

# Checklist final antes de mandar el correo

Hacerlo en este orden, sin saltar pasos.

☐ Las 6 DBs de Notion existen y tienen los datos del seed
☐ La integración de Notion está conectada a la página padre
☐ `populate_notion.py` corrió sin errores y los 3 informes están visibles
☐ Backend local procesa los 3 casos correctamente
☐ Frontend local muestra trace y decisión correctos para los 3 casos
☐ Repo pusheado a GitHub, sin el `.env` (revisar el `.gitignore`)
☐ Backend deployado en Render con todas las env vars
☐ `https://tu-backend.onrender.com/health` devuelve
`{"ok": true}` desde modo incógnito
☐ Frontend deployado en Streamlit Cloud con `BACKEND_URL` en secrets
☐ Crédito de Anthropic ≥ $5
☐ Cuota de Notion no agotada
☐ Backend despertado con un ping antes del envío
☐ Probado el link público desde el celular en datos móviles y los 3 casos funcionan
☐ README tiene link al deploy en la primera pantalla
☐ Correo redactado, listo para mandar

37 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Plan de timeboxing

|  Bloque | Tiempo | Tarea  |
| --- | --- | --- |
|  0 | 45 min | Notion: crear las 6 DBs, sembrar datos demo  |
|  1 | 90 min | models.py , notion_client.py , tools.py  |
|  2 | 60 min | agent.py con loop de tool use  |
|  3 | 60 min | app.py Streamlit con dropdown + trace  |
|  4 | 30 min | Ajuste fino del prompt con los 3 casos  |
|  5 | 45 min | Deploy + prueba en otro dispositivo + README  |

Total: ~5 horas netas. Si pasan de 6 horas, están sobre-ingenierizando.

38 / 40

Pre-Autorización Quirúrgica - hacklAthon

# Fallback monolítico

Si el deploy doble pelea o consume más de 45 minutos, colapsar todo a un solo Streamlit: borrar main.py, copiar agent.py, tools.py, notion_client.py, models.py, prompts.py al directorio frontend/, y en app.py reemplazar las llamadas HTTP por:

```python
from agent import run_agent
import notion_client as nc

# En lugar de requests.get(f"{BACKEND_URL}/informes")
informes = nc.list_informes()

# En lugar de requests.post(f"{BACKEND_URL}/procesar/...")
data = run_agent(informe_id)
```

Las env vars van en secrets.toml de Streamlit. Una sola cosa que deployar, una sola URL pública. Si el deploy doble cuesta más de 45 minutos, colapsar.

39 / 40

Pre-Autorización Quirúrgica - hackIAthon

# Correo de envío

Asunto: Entregable hackIAthon – Reto 1 – [nombres del equipo]

Buenas tardes,

Adjunto los entregables del reto inicial. Escogimos el reto 1
(Pre-Autorización Quirúrgica).

- Agente funcional: [link]
- Repositorio: [link]

El README incluye los 3 casos demo precargados (aprobación, rechazo
por carencia, documentos faltantes) y las instrucciones para
correrlo local.

Saludos,
[equipo]

Sin emojis, sin explicar arquitectura, sin disculpas. Sobrio y profesional.

40 / 40



