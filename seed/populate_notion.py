"""
Crea las 6 DBs en Notion y siembra datos demo.

Requisitos previos en backend/.env:
  - NOTION_TOKEN          : token de la integracion interna
  - NOTION_PARENT_PAGE_ID : ID de la pagina padre con la integracion conectada

Uso:
  python seed/populate_notion.py

Despues de correr, copia los IDs que imprime al final en backend/.env.
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from notion_client import Client

# ---------- Setup ----------
ENV_PATH = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(ENV_PATH)

TOKEN = os.environ.get("NOTION_TOKEN")
PARENT = os.environ.get("NOTION_PARENT_PAGE_ID")

if not TOKEN or not PARENT:
    print(
        "ERROR: faltan NOTION_TOKEN o NOTION_PARENT_PAGE_ID en backend/.env\n"
        "Sigue docs/notion_setup.md antes de correr este script."
    )
    sys.exit(1)

notion = Client(auth=TOKEN)
HOY = date.today()

DOCS_OPTIONS = [
    {"name": "informe_quirurgico"},
    {"name": "examenes_prequirurgicos"},
    {"name": "segundo_dictamen"},
    {"name": "exames_imagen"},
    {"name": "consentimiento"},
]


DB_TO_DS: dict[str, str] = {}


def crear_db(title: str, properties: dict) -> str:
    r = notion.databases.create(
        parent={"type": "page_id", "page_id": PARENT},
        title=[{"type": "text", "text": {"content": title}}],
        initial_data_source={"properties": properties},
    )
    db_id = r["id"]
    ds_id = r["data_sources"][0]["id"]
    DB_TO_DS[db_id] = ds_id
    print(f"  -> {title}")
    return db_id


def relation(target_db_id: str) -> dict:
    return {
        "relation": {
            "data_source_id": DB_TO_DS[target_db_id],
            "type": "single_property",
            "single_property": {},
        }
    }


# ---------- 1. Crear DBs ----------
print("Creando DBs en Notion...")

db_planes = crear_db(
    "Planes",
    {
        "nombre": {"title": {}},
        "nivel": {
            "select": {
                "options": [
                    {"name": "Basico"},
                    {"name": "Estandar"},
                    {"name": "Premium"},
                ]
            }
        },
    },
)

db_asegurados = crear_db(
    "Asegurados",
    {
        "cedula": {"title": {}},
        "nombre": {"rich_text": {}},
        "fecha_nacimiento": {"date": {}},
    },
)

db_polizas = crear_db(
    "Polizas",
    {
        "numero": {"title": {}},
        "titular": relation(db_asegurados),
        "plan": relation(db_planes),
        "fecha_alta": {"date": {}},
        "estado": {
            "select": {
                "options": [
                    {"name": "Vigente"},
                    {"name": "Suspendida"},
                    {"name": "Cancelada"},
                    {"name": "Vencida"},
                ]
            }
        },
    },
)

# Asegurados.poliza -> Polizas (update porque era circular)
notion.data_sources.update(
    data_source_id=DB_TO_DS[db_asegurados],
    properties={"poliza": relation(db_polizas)},
)
print("  -> Asegurados.poliza relation linked")

db_coberturas = crear_db(
    "Coberturas",
    {
        "id": {"title": {}},
        "plan": relation(db_planes),
        "codigo_cpt": {"rich_text": {}},
        "descripcion": {"rich_text": {}},
        "cubierto": {"checkbox": {}},
        "dias_carencia": {"number": {"format": "number"}},
        "documentos_requeridos": {"multi_select": {"options": DOCS_OPTIONS}},
    },
)

db_informes = crear_db(
    "Informes_Medicos",
    {
        "id_informe": {"title": {}},
        "paciente": relation(db_asegurados),
        "fecha_emision": {"date": {}},
        "hospital": {"rich_text": {}},
        "medico_tratante": {"rich_text": {}},
        "diagnostico_cie10": {"rich_text": {}},
        "procedimiento_cpt": {"rich_text": {}},
        "descripcion_procedimiento": {"rich_text": {}},
        "justificacion_clinica": {"rich_text": {}},
        "fecha_programada": {"date": {}},
        "documentos_adjuntos": {"multi_select": {"options": DOCS_OPTIONS}},
    },
)

db_decisiones = crear_db(
    "Decisiones",
    {
        "id_decision": {"title": {}},
        "informe": relation(db_informes),
        "decision": {
            "select": {
                "options": [
                    {"name": "Aprobado"},
                    {"name": "Negado"},
                    {"name": "Documentos_Faltantes"},
                ]
            }
        },
        "justificacion": {"rich_text": {}},
        "clausula_aplicada": {"rich_text": {}},
        "documentos_faltantes": {"multi_select": {"options": DOCS_OPTIONS}},
        "timestamp": {"date": {}},
    },
)


# ---------- 2. Sembrar planes ----------
print("\nSembrando planes...")


def crear_plan(nombre: str, nivel: str) -> str:
    r = notion.pages.create(
        parent={"database_id": db_planes},
        properties={
            "nombre": {"title": [{"text": {"content": nombre}}]},
            "nivel": {"select": {"name": nivel}},
        },
    )
    return r["id"]


plan_basico = crear_plan("Plan Salud Basico", "Basico")
plan_estandar = crear_plan("Plan Salud Estandar", "Estandar")
plan_premium = crear_plan("Plan Salud Premium", "Premium")
print("  -> 3 planes")


# ---------- 3. Sembrar coberturas ----------
print("\nSembrando coberturas...")


def crear_cobertura(plan_id, cpt, desc, cubierto, dias_carencia, docs_req):
    notion.pages.create(
        parent={"database_id": db_coberturas},
        properties={
            "id": {"title": [{"text": {"content": f"COB-{cpt}-{plan_id[:4]}"}}]},
            "plan": {"relation": [{"id": plan_id}]},
            "codigo_cpt": {"rich_text": [{"text": {"content": cpt}}]},
            "descripcion": {"rich_text": [{"text": {"content": desc}}]},
            "cubierto": {"checkbox": cubierto},
            "dias_carencia": {"number": dias_carencia},
            "documentos_requeridos": {
                "multi_select": [{"name": d} for d in docs_req]
            },
        },
    )


# Apendicectomia (44970)
crear_cobertura(plan_basico, "44970", "Apendicectomia laparoscopica", True, 90,
                ["informe_quirurgico", "examenes_prequirurgicos"])
crear_cobertura(plan_estandar, "44970", "Apendicectomia laparoscopica", True, 60,
                ["informe_quirurgico", "examenes_prequirurgicos"])
crear_cobertura(plan_premium, "44970", "Apendicectomia laparoscopica", True, 30,
                ["informe_quirurgico"])

# Colecistectomia (47562)
crear_cobertura(plan_estandar, "47562", "Colecistectomia laparoscopica", True, 90,
                ["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"])
crear_cobertura(plan_premium, "47562", "Colecistectomia laparoscopica", True, 30,
                ["informe_quirurgico", "examenes_prequirurgicos"])

# Cirugia bariatrica (43644)
crear_cobertura(plan_estandar, "43644", "Cirugia bariatrica - bypass gastrico", True, 365,
                ["informe_quirurgico", "examenes_prequirurgicos",
                 "segundo_dictamen", "exames_imagen"])
crear_cobertura(plan_premium, "43644", "Cirugia bariatrica - bypass gastrico", True, 180,
                ["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"])
crear_cobertura(plan_basico, "43644", "Cirugia bariatrica - bypass gastrico", False, 0, [])

print("  -> 8 coberturas")


# ---------- 4. Sembrar asegurados + polizas ----------
print("\nSembrando asegurados y polizas...")


def crear_asegurado(cedula: str, nombre: str, fnac: date) -> str:
    r = notion.pages.create(
        parent={"database_id": db_asegurados},
        properties={
            "cedula": {"title": [{"text": {"content": cedula}}]},
            "nombre": {"rich_text": [{"text": {"content": nombre}}]},
            "fecha_nacimiento": {"date": {"start": fnac.isoformat()}},
        },
    )
    return r["id"]


def crear_poliza(numero: str, titular_id: str, plan_id: str,
                 fecha_alta: date, estado: str) -> str:
    r = notion.pages.create(
        parent={"database_id": db_polizas},
        properties={
            "numero": {"title": [{"text": {"content": numero}}]},
            "titular": {"relation": [{"id": titular_id}]},
            "plan": {"relation": [{"id": plan_id}]},
            "fecha_alta": {"date": {"start": fecha_alta.isoformat()}},
            "estado": {"select": {"name": estado}},
        },
    )
    notion.pages.update(
        titular_id,
        properties={"poliza": {"relation": [{"id": r["id"]}]}},
    )
    return r["id"]


# Caso A: Premium + 2 anios -> aprobacion limpia
a1 = crear_asegurado("0912345678", "Juan Perez Andrade", date(1985, 5, 12))
crear_poliza("POL-001", a1, plan_premium, HOY - timedelta(days=730), "Vigente")

# Caso B: Estandar + 45 dias -> rechazo por carencia
a2 = crear_asegurado("0923456789", "Maria Gonzalez Vera", date(1978, 9, 3))
crear_poliza("POL-002", a2, plan_estandar, HOY - timedelta(days=45), "Vigente")

# Caso C: Estandar + 1 anio -> documentos faltantes
a3 = crear_asegurado("0934567890", "Carlos Bermeo Loja", date(1990, 1, 22))
crear_poliza("POL-003", a3, plan_estandar, HOY - timedelta(days=365), "Vigente")

print("  -> 3 asegurados, 3 polizas")


# ---------- 5. Sembrar informes ----------
print("\nSembrando informes medicos...")


def crear_informe(id_inf, paciente_id, hospital, medico, cie10, cpt, desc,
                  justif, dias_futuro, docs):
    notion.pages.create(
        parent={"database_id": db_informes},
        properties={
            "id_informe": {"title": [{"text": {"content": id_inf}}]},
            "paciente": {"relation": [{"id": paciente_id}]},
            "fecha_emision": {"date": {"start": HOY.isoformat()}},
            "hospital": {"rich_text": [{"text": {"content": hospital}}]},
            "medico_tratante": {"rich_text": [{"text": {"content": medico}}]},
            "diagnostico_cie10": {"rich_text": [{"text": {"content": cie10}}]},
            "procedimiento_cpt": {"rich_text": [{"text": {"content": cpt}}]},
            "descripcion_procedimiento": {
                "rich_text": [{"text": {"content": desc}}]
            },
            "justificacion_clinica": {
                "rich_text": [{"text": {"content": justif}}]
            },
            "fecha_programada": {
                "date": {"start": (HOY + timedelta(days=dias_futuro)).isoformat()}
            },
            "documentos_adjuntos": {
                "multi_select": [{"name": d} for d in docs]
            },
        },
    )


crear_informe(
    "INF-001", a1, "Hospital Metropolitano", "Dr. Velasquez",
    "K35.9", "44970", "Apendicectomia laparoscopica",
    "Paciente con dolor abdominal en fosa iliaca derecha, leucocitosis, "
    "ecografia confirma apendicitis aguda. Indicacion quirurgica urgente.",
    2, ["informe_quirurgico", "examenes_prequirurgicos"],
)

crear_informe(
    "INF-002", a2, "Hospital Vozandes", "Dra. Mora",
    "E66.01", "43644", "Cirugia bariatrica - bypass gastrico",
    "Paciente con IMC 41, comorbilidades metabolicas, falla terapia "
    "conservadora 18 meses. Candidata a manejo quirurgico.",
    14, ["informe_quirurgico", "examenes_prequirurgicos", "segundo_dictamen"],
)

crear_informe(
    "INF-003", a3, "Hospital Alcivar", "Dr. Mendoza",
    "K80.20", "47562", "Colecistectomia laparoscopica",
    "Paciente con colelitiasis sintomatica, episodios de colico biliar "
    "recurrentes, ecografia con calculo de 2cm. Indicacion quirurgica electiva.",
    7, ["informe_quirurgico"],
)

print("  -> 3 informes")


# ---------- 6. Imprimir IDs ----------
print("\n" + "=" * 60)
print("LISTO. Pega esto en backend/.env y guarda:")
print("=" * 60)
print(f"NOTION_DB_ASEGURADOS={DB_TO_DS[db_asegurados]}")
print(f"NOTION_DB_POLIZAS={DB_TO_DS[db_polizas]}")
print(f"NOTION_DB_PLANES={DB_TO_DS[db_planes]}")
print(f"NOTION_DB_COBERTURAS={DB_TO_DS[db_coberturas]}")
print(f"NOTION_DB_INFORMES={DB_TO_DS[db_informes]}")
print(f"NOTION_DB_DECISIONES={DB_TO_DS[db_decisiones]}")
print("=" * 60)
print("\nVerifica en Notion: deberias ver 6 DBs en tu pagina padre,")
print("con 3 planes, 8 coberturas, 3 asegurados, 3 polizas y 3 informes.")
