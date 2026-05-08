"""Cliente Notion: lectura de informes/asegurados/polizas/coberturas y persistencia
de decisiones. Las funciones publicas son las que invocan los tools del agente.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from notion_client import Client

from app.config import settings

notion = Client(auth=settings.NOTION_TOKEN)


# ---------- Errores ----------

class NotFound(Exception):
    pass


# ---------- Extractores de propiedades ----------

def _title(prop: dict) -> str:
    return "".join(t.get("plain_text", "") for t in (prop.get("title") or []))


def _rich_text(prop: dict) -> str:
    return "".join(t.get("plain_text", "") for t in (prop.get("rich_text") or []))


def _select(prop: dict) -> Optional[str]:
    sel = prop.get("select")
    return sel.get("name") if sel else None


def _multi_select(prop: dict) -> list[str]:
    return [opt["name"] for opt in (prop.get("multi_select") or [])]


def _date(prop: dict) -> Optional[str]:
    d = prop.get("date")
    return d.get("start") if d else None


def _number(prop: dict) -> Optional[float]:
    return prop.get("number")


def _checkbox(prop: dict) -> bool:
    return bool(prop.get("checkbox"))


def _relation_ids(prop: dict) -> list[str]:
    return [r["id"] for r in (prop.get("relation") or [])]


def _query_one(data_source_id: str, filter_: dict) -> Optional[dict]:
    r = notion.data_sources.query(
        data_source_id=data_source_id, filter=filter_, page_size=1
    )
    results = r.get("results") or []
    return results[0] if results else None


# ---------- Lectores por DB ----------

def _read_asegurado(page: dict) -> dict:
    p = page["properties"]
    return {
        "page_id": page["id"],
        "cedula": _title(p["cedula"]),
        "nombre": _rich_text(p["nombre"]),
        "fecha_nacimiento": _date(p["fecha_nacimiento"]),
        "poliza_relation_ids": _relation_ids(p.get("poliza", {})),
    }


def _read_poliza(page: dict) -> dict:
    p = page["properties"]
    return {
        "page_id": page["id"],
        "numero": _title(p["numero"]),
        "estado": _select(p["estado"]),
        "fecha_alta": _date(p["fecha_alta"]),
        "titular_relation_ids": _relation_ids(p["titular"]),
        "plan_relation_ids": _relation_ids(p["plan"]),
    }


def _read_plan(page: dict) -> dict:
    p = page["properties"]
    return {
        "page_id": page["id"],
        "nombre": _title(p["nombre"]),
        "nivel": _select(p["nivel"]),
    }


def _read_cobertura(page: dict) -> dict:
    p = page["properties"]
    return {
        "page_id": page["id"],
        "id": _title(p["id"]),
        "codigo_cpt": _rich_text(p["codigo_cpt"]),
        "descripcion": _rich_text(p["descripcion"]),
        "cubierto": _checkbox(p["cubierto"]),
        "dias_carencia": _number(p["dias_carencia"]),
        "documentos_requeridos": _multi_select(p["documentos_requeridos"]),
    }


def _read_informe(page: dict) -> dict:
    p = page["properties"]
    return {
        "page_id": page["id"],
        "id_informe": _title(p["id_informe"]),
        "fecha_emision": _date(p["fecha_emision"]),
        "hospital": _rich_text(p["hospital"]),
        "medico_tratante": _rich_text(p["medico_tratante"]),
        "diagnostico_cie10": _rich_text(p["diagnostico_cie10"]),
        "procedimiento_cpt": _rich_text(p["procedimiento_cpt"]),
        "descripcion_procedimiento": _rich_text(p["descripcion_procedimiento"]),
        "justificacion_clinica": _rich_text(p["justificacion_clinica"]),
        "fecha_programada": _date(p["fecha_programada"]),
        "documentos_adjuntos": _multi_select(p["documentos_adjuntos"]),
        "paciente_relation_ids": _relation_ids(p["paciente"]),
    }


# ---------- API publica (consumida por los tools del agente) ----------

def fetch_informe(id_informe: str) -> dict:
    """Devuelve el informe medico junto con los datos del paciente referenciado."""
    page = _query_one(
        settings.NOTION_DB_INFORMES,
        {"property": "id_informe", "title": {"equals": id_informe}},
    )
    if not page:
        raise NotFound(f"Informe {id_informe} no encontrado")
    informe = _read_informe(page)

    paciente: Optional[dict] = None
    if informe["paciente_relation_ids"]:
        pat_page = notion.pages.retrieve(informe["paciente_relation_ids"][0])
        paciente = _read_asegurado(pat_page)

    return {"informe": informe, "paciente": paciente}


def fetch_cobertura(cedula: str, codigo_cpt: str) -> dict:
    """Devuelve poliza + plan + cobertura para la cedula y procedimiento dados.

    cobertura sera None si el plan del asegurado no tiene cobertura registrada
    para ese codigo_cpt (procedimiento no incluido en el plan).
    """
    aseg_page = _query_one(
        settings.NOTION_DB_ASEGURADOS,
        {"property": "cedula", "title": {"equals": cedula}},
    )
    if not aseg_page:
        raise NotFound(f"Asegurado con cedula {cedula} no encontrado")
    asegurado = _read_asegurado(aseg_page)

    if not asegurado["poliza_relation_ids"]:
        raise NotFound(f"Asegurado {cedula} no tiene poliza asociada")
    poliza_page = notion.pages.retrieve(asegurado["poliza_relation_ids"][0])
    poliza = _read_poliza(poliza_page)

    plan: Optional[dict] = None
    if poliza["plan_relation_ids"]:
        plan_page = notion.pages.retrieve(poliza["plan_relation_ids"][0])
        plan = _read_plan(plan_page)

    cobertura: Optional[dict] = None
    if plan:
        cob_page = _query_one(
            settings.NOTION_DB_COBERTURAS,
            {
                "and": [
                    {"property": "plan", "relation": {"contains": plan["page_id"]}},
                    {"property": "codigo_cpt", "rich_text": {"equals": codigo_cpt}},
                ]
            },
        )
        if cob_page:
            cobertura = _read_cobertura(cob_page)

    return {
        "asegurado": asegurado,
        "poliza": poliza,
        "plan": plan,
        "cobertura": cobertura,
    }


def list_informes_summary(page_size: int = 100) -> list[dict]:
    """Lista resumida de informes medicos (id, descripcion, hospital) para la
    bandeja del front. Pagina hasta agotar la DB."""
    out: list[dict] = []
    cursor: Optional[str] = None
    while True:
        kwargs: dict[str, Any] = {
            "data_source_id": settings.NOTION_DB_INFORMES,
            "page_size": page_size,
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        r = notion.data_sources.query(**kwargs)
        for page in r.get("results", []):
            p = page["properties"]
            out.append(
                {
                    "id_informe": _title(p["id_informe"]),
                    "descripcion_procedimiento": _rich_text(p["descripcion_procedimiento"]),
                    "hospital": _rich_text(p["hospital"]),
                }
            )
        if not r.get("has_more"):
            break
        cursor = r.get("next_cursor")
    return out


def fetch_informe_full(id_informe: str) -> dict:
    """Detalle enriquecido del informe: datos del informe + paciente + poliza
    + plan, en shape plano (lo que espera el front)."""
    base = fetch_informe(id_informe)
    informe = base["informe"]
    paciente = base.get("paciente") or {}

    poliza: dict = {}
    plan: dict = {}
    if paciente.get("poliza_relation_ids"):
        pol_page = notion.pages.retrieve(paciente["poliza_relation_ids"][0])
        poliza = _read_poliza(pol_page)
        if poliza.get("plan_relation_ids"):
            plan_page = notion.pages.retrieve(poliza["plan_relation_ids"][0])
            plan = _read_plan(plan_page)

    return {
        "id_informe": informe.get("id_informe", ""),
        "paciente_cedula": paciente.get("cedula", "") or "",
        "paciente_nombre": paciente.get("nombre", "") or "",
        "paciente_fecha_nacimiento": paciente.get("fecha_nacimiento", "") or "",
        "paciente_sexo": "",
        "poliza_numero": poliza.get("numero", "") or "",
        "plan_nombre": plan.get("nombre", "") or "",
        "plan_nivel": plan.get("nivel", "") or "",
        "plan_id": plan.get("page_id", "") or "",
        "poliza_fecha_alta": poliza.get("fecha_alta", "") or "",
        "poliza_estado": poliza.get("estado", "") or "",
        "fecha_emision": informe.get("fecha_emision", "") or "",
        "hospital": informe.get("hospital", "") or "",
        "medico_tratante": informe.get("medico_tratante", "") or "",
        "diagnostico_cie10": informe.get("diagnostico_cie10", "") or "",
        "diagnostico_desc": "",
        "procedimiento_cpt": informe.get("procedimiento_cpt", "") or "",
        "descripcion_procedimiento": informe.get("descripcion_procedimiento", "") or "",
        "justificacion_clinica": informe.get("justificacion_clinica", "") or "",
        "fecha_programada": informe.get("fecha_programada", "") or "",
        "urgencia": "",
        "documentos_adjuntos": list(informe.get("documentos_adjuntos") or []),
    }


def fetch_cobertura_by_plan_page(codigo_cpt: str, plan_page_id: str) -> Optional[dict]:
    """Devuelve la regla de cobertura para (CPT, plan), o None si no existe."""
    page = _query_one(
        settings.NOTION_DB_COBERTURAS,
        {
            "and": [
                {"property": "plan", "relation": {"contains": plan_page_id}},
                {"property": "codigo_cpt", "rich_text": {"equals": codigo_cpt}},
            ]
        },
    )
    if not page:
        return None
    cob = _read_cobertura(page)
    return {
        "cubierto": cob["cubierto"],
        "dias_carencia": int(cob.get("dias_carencia") or 0),
        "documentos_requeridos": cob.get("documentos_requeridos") or [],
    }


def submit_decision(
    id_informe: str,
    decision: str,
    justificacion: str,
    clausula_aplicada: Optional[str] = None,
    documentos_faltantes: Optional[list[str]] = None,
) -> dict:
    """Crea una fila en la DB Decisiones ligada al informe."""
    informe_page = _query_one(
        settings.NOTION_DB_INFORMES,
        {"property": "id_informe", "title": {"equals": id_informe}},
    )
    if not informe_page:
        raise NotFound(f"Informe {id_informe} no encontrado para guardar decision")

    timestamp = datetime.now(timezone.utc)
    id_decision = f"DEC-{id_informe}-{int(timestamp.timestamp())}"

    properties: dict[str, Any] = {
        "id_decision": {"title": [{"text": {"content": id_decision}}]},
        "informe": {"relation": [{"id": informe_page["id"]}]},
        "decision": {"select": {"name": decision}},
        "justificacion": {"rich_text": [{"text": {"content": justificacion}}]},
        "timestamp": {"date": {"start": timestamp.isoformat()}},
    }
    if clausula_aplicada:
        properties["clausula_aplicada"] = {
            "rich_text": [{"text": {"content": clausula_aplicada}}]
        }
    if documentos_faltantes:
        properties["documentos_faltantes"] = {
            "multi_select": [{"name": d} for d in documentos_faltantes]
        }

    notion.pages.create(
        parent={"data_source_id": settings.NOTION_DB_DECISIONES},
        properties=properties,
    )

    return {"id_decision": id_decision, "timestamp": timestamp.isoformat()}
