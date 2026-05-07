"""Agente de pre-autorizacion: tool-use loop con Anthropic SDK.

El agente recibe (id_informe, cedula), invoca tools que leen Notion, valida
vigencia/cobertura/carencia/documentos y persiste la decision en Notion.
"""
import json
from datetime import date
from typing import Any, Optional

from anthropic import Anthropic

from app.config import settings
from app.models.schemas import AuthorizeResponse, Decision
from app.services import notion_service

client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


SYSTEM_PROMPT = """\
Eres un agente de pre-autorizacion de cirugias para una aseguradora.
Decides si un informe medico se aprueba, niega o requiere documentos.

Sigue ESTE flujo en este orden. Detente en el primer paso fallido y procede al
paso 9 con la decision correspondiente:

1. Llama fetch_informe(id_informe) para obtener el informe y los datos del paciente.

2. Validacion paciente: paciente.cedula DEBE coincidir con la cedula del request.
   Si NO coincide -> decision="Negado",
                     clausula_aplicada="informe no corresponde al paciente",
                     documentos_faltantes=[].

3. Llama fetch_cobertura(cedula, informe.procedimiento_cpt).

4. Vigencia: poliza.estado debe ser exactamente "Vigente".
   Si no -> decision="Negado",
            clausula_aplicada="poliza no vigente (estado: <estado>)".

5. Cobertura: cobertura no debe ser null y cobertura.cubierto debe ser true.
   Si no -> decision="Negado",
            clausula_aplicada="procedimiento <codigo_cpt> no cubierto por el plan <plan.nombre>".

6. Carencia: dias transcurridos desde poliza.fecha_alta hasta HOY deben ser
   >= cobertura.dias_carencia.
   Si no -> decision="Negado",
            clausula_aplicada="periodo de carencia incumplido (requeridos: X dias, transcurridos: Y dias)".

7. Documentos: cada item de cobertura.documentos_requeridos DEBE estar en
   informe.documentos_adjuntos.
   Si faltan -> decision="Documentos_Faltantes",
                clausula_aplicada="documentos requeridos por la cobertura del plan",
                documentos_faltantes=<lista exacta de los que faltan>.

8. Si pasos 4-7 OK -> decision="Aprobado",
                      clausula_aplicada="cobertura vigente y documentacion completa",
                      documentos_faltantes=[].

9. Llama submit_decision EXACTAMENTE UNA VEZ con la conclusion.
10. Termina sin responder mas texto.

Reglas duras:
- justificacion debe citar datos concretos (codigo_cpt, dias, plan, etc.).
- decision solo puede ser: Aprobado, Negado, Documentos_Faltantes.
- documentos_faltantes es siempre una lista (vacia si no aplica).
- Una sola llamada a submit_decision por flujo.
"""


TOOLS: list[dict[str, Any]] = [
    {
        "name": "fetch_informe",
        "description": (
            "Obtiene el informe medico por su id_informe (ej. INF-001) junto con "
            "los datos del paciente al que pertenece (cedula, nombre, fecha_nacimiento)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id_informe": {"type": "string"},
            },
            "required": ["id_informe"],
        },
    },
    {
        "name": "fetch_cobertura",
        "description": (
            "Obtiene la poliza del asegurado (por cedula), el plan asociado y la "
            "cobertura especifica para un codigo_cpt. Si el plan no tiene cobertura "
            "registrada para ese procedimiento, cobertura sera null."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cedula": {"type": "string"},
                "codigo_cpt": {"type": "string"},
            },
            "required": ["cedula", "codigo_cpt"],
        },
    },
    {
        "name": "submit_decision",
        "description": (
            "Persiste la decision final en la DB Decisiones de Notion, ligada al "
            "informe. Llamar EXACTAMENTE UNA VEZ al cierre del flujo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id_informe": {"type": "string"},
                "decision": {
                    "type": "string",
                    "enum": ["Aprobado", "Negado", "Documentos_Faltantes"],
                },
                "justificacion": {"type": "string"},
                "clausula_aplicada": {"type": "string"},
                "documentos_faltantes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "id_informe",
                "decision",
                "justificacion",
                "clausula_aplicada",
                "documentos_faltantes",
            ],
        },
    },
]


MAX_ITERATIONS = 10


class AgentError(Exception):
    pass


def run_authorization(id_informe: str, cedula: str) -> AuthorizeResponse:
    decision_record: Optional[dict[str, Any]] = None
    last_submit_input: Optional[dict[str, Any]] = None

    def _dispatch(name: str, args: dict) -> dict:
        nonlocal decision_record, last_submit_input
        if name == "fetch_informe":
            return notion_service.fetch_informe(args["id_informe"])
        if name == "fetch_cobertura":
            return notion_service.fetch_cobertura(args["cedula"], args["codigo_cpt"])
        if name == "submit_decision":
            last_submit_input = args
            decision_record = notion_service.submit_decision(
                id_informe=args["id_informe"],
                decision=args["decision"],
                justificacion=args["justificacion"],
                clausula_aplicada=args.get("clausula_aplicada"),
                documentos_faltantes=args.get("documentos_faltantes") or [],
            )
            return decision_record
        raise AgentError(f"Tool desconocida: {name}")

    user_msg = (
        f"Procesa la pre-autorizacion del informe id_informe={id_informe} "
        f"para cedula={cedula}. Hoy es {date.today().isoformat()}. "
        f"Sigue el flujo y al final llama submit_decision."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

    for _ in range(MAX_ITERATIONS):
        resp = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=TOOLS,
            thinking={"type": "adaptive"},
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            break

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                result = _dispatch(block.name, block.input)
                content = json.dumps(result, default=str, ensure_ascii=False)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    }
                )
            except Exception as exc:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                        "is_error": True,
                    }
                )
        messages.append({"role": "user", "content": tool_results})
    else:
        raise AgentError("Limite de iteraciones excedido sin emitir decision")

    if decision_record is None or last_submit_input is None:
        raise AgentError("El agente termino sin llamar submit_decision")

    return AuthorizeResponse(
        id_informe=last_submit_input["id_informe"],
        cedula=cedula,
        decision=Decision(last_submit_input["decision"]),
        justificacion=last_submit_input["justificacion"],
        clausula_aplicada=last_submit_input.get("clausula_aplicada"),
        documentos_faltantes=last_submit_input.get("documentos_faltantes") or [],
        id_decision=decision_record["id_decision"],
        timestamp=decision_record["timestamp"],
    )
