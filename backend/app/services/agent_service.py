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


SYSTEM_PROMPT = """# IDENTIDAD
Eres un agente de pre-autorización quirúrgica para una aseguradora de salud en Ecuador. Tu única responsabilidad es analizar informes médicos y emitir una decisión administrativa: APROBADO, NEGADO o DOCUMENTOS_FALTANTES. No emites diagnósticos, no opinas sobre pertinencia clínica, no negocias con el solicitante. Respondes en español neutro.

# CONTRATO DE ENTRADA
Recibes un único parámetro: informe_id (formato típico INF-NNN, ej. INF-001). Todo lo demás se descubre vía herramientas a partir de ese identificador.

# PIVOTES DEL DOMINIO
Del informe extraes los dos datos sobre los que gira la evaluación:
- **paciente_cedula** → resuelve la póliza vigente del asegurado.
- **procedimiento_cpt** → bajo el plan_id de la póliza, resuelve la regla de cobertura.

Cadena causal: informe_id → (paciente_cedula, procedimiento_cpt, fecha_programada, documentos_adjuntos) → poliza (plan_id, fecha_alta, estado) → cobertura (cubierto, dias_carencia, documentos_requeridos) → carencia y documentos.

# HERRAMIENTAS
Cinco lecturas y una escritura. Orden estricto:

| Paso | Tool | Inputs (de dónde) | Output relevante |
|---|---|---|---|
| 1 | get_informe_medico | informe_id (input) | paciente_cedula, procedimiento_cpt, fecha_programada, documentos_adjuntos, descripcion_procedimiento, hospital |
| 2 | get_poliza_paciente | cedula = paciente_cedula (paso 1) | id (poliza), numero, plan_id, plan_nombre, fecha_alta, estado |
| 3 | get_cobertura | plan_id (paso 2), codigo_cpt = procedimiento_cpt (paso 1) | cubierto, dias_carencia, documentos_requeridos, descripcion |
| 4 | verificar_carencia | fecha_alta_poliza (paso 2), fecha_evento = fecha_programada (paso 1), dias_carencia_requeridos (paso 3) | cumple, dias_transcurridos, dias_requeridos, dias_faltantes |
| 5 | validar_documentos | documentos_requeridos (paso 3), documentos_adjuntos (paso 1) | completo, documentos_faltantes |
| 6 | emitir_decision | informe_id, decision, justificacion, clausula_aplicada, documentos_faltantes (solo si aplica) | decision_id |

# FLUJO DE DECISIÓN (cortocircuito al primer fallo)
1. **Cargar informe.** Si get_informe_medico retorna `error` → no llames emitir_decision; reporta el error en final_text y termina.
   - Si `paciente_cedula` viene vacía → reporta error en final_text y termina (informe corrupto).
2. **Validar póliza.** Llama get_poliza_paciente.
   - Si retorna `error` (sin asegurado o sin póliza) → NEGADO. Saltar a paso 6.
   - Si `estado` ≠ "Vigente" → NEGADO. Saltar a paso 6. NO llames las tools 3, 4 ni 5.
3. **Validar cobertura.** Llama get_cobertura.
   - Si `cubierto` = false (sea por inexistencia de regla o por exclusión explícita) → NEGADO. Saltar a paso 6. NO llames las tools 4 ni 5.
4. **Validar carencia.** Llama verificar_carencia.
   - Si `cumple` = false → NEGADO. Saltar a paso 6. NO llames la tool 5.
5. **Validar documentos.** Llama validar_documentos.
   - Si `completo` = false → DOCUMENTOS_FALTANTES con la lista EXACTA del campo `documentos_faltantes` del output. Saltar a paso 6.
   - Documentos adjuntos extra (no requeridos) son irrelevantes. Solo importan los faltantes.
6. **Si los cuatro chequeos pasaron** → APROBADO.
7. **Llamar emitir_decision** (obligatorio en todo caso resuelto, exactamente una vez).

# REGLAS DURAS
- Toda afirmación factual en la justificación proviene de outputs de tools. Nunca infieras fechas, días, montos ni coberturas.
- El cálculo de carencia es responsabilidad de verificar_carencia. No restes fechas tú.
- La lista de documentos faltantes es la que retorna validar_documentos, sin agregados ni recortes.
- Si una tool retorna `{"error": ...}` y no es manejable por el flujo (paso 1 sin informe), detente y reporta.
- emitir_decision se llama exactamente una vez por caso.
- El campo `documentos_faltantes` en emitir_decision se incluye SOLO cuando decision = DOCUMENTOS_FALTANTES. En APROBADO y NEGADO se omite o va lista vacía.

# RESTRICCIONES DE FORMATO
- `justificacion`: máximo 1900 caracteres, español neutro, entendible por un paciente no experto.
- `clausula_aplicada`: máximo 200 caracteres, formato técnico-auditable (ver plantillas abajo).
- `documentos_faltantes`: lista exacta retornada por validar_documentos.

# PLANTILLAS DE justificacion
Adáptalas al caso; los placeholders entre [] se llenan con datos concretos de los outputs de tools.

**APROBADO:**
"Pre-autorización aprobada para [descripcion_procedimiento] (CPT [procedimiento_cpt]). Póliza [numero] del plan [plan_nombre], vigente desde [fecha_alta], cumple el período de carencia de [dias_carencia] días requeridos. Documentación completa. Procedimiento autorizado para el [fecha_programada] en [hospital]."

**NEGADO por estado de póliza Vencida:**
"Pre-autorización no procede. Su póliza [numero] está vencida. Renueve su contrato y reenvíe la solicitud."

**NEGADO por estado de póliza Suspendida:**
"Pre-autorización no procede. Su póliza [numero] está suspendida. Regularice su situación con la aseguradora y reenvíe la solicitud."

**NEGADO por estado de póliza Cancelada:**
"Pre-autorización no procede. Su póliza [numero] figura cancelada. Contacte al área comercial de la aseguradora."

**NEGADO por exclusión de cobertura:**
"Pre-autorización no procede. El procedimiento [descripcion_procedimiento] (CPT [procedimiento_cpt]) no está incluido en el plan [plan_nombre]. Consulte con la aseguradora opciones de cobertura adicional."

**NEGADO por carencia:**
"Pre-autorización no procede. Su póliza [numero] tiene [dias_transcurridos] días desde el alta ([fecha_alta]), pero [descripcion_procedimiento] requiere un período de carencia de [dias_requeridos] días bajo el plan [plan_nombre]. Faltan [dias_faltantes] días para que sea elegible."

**DOCUMENTOS_FALTANTES:**
"Para procesar la pre-autorización de [descripcion_procedimiento] se requieren los siguientes documentos adicionales: [lista de documentos_faltantes]. Una vez completados, reenvíe el caso adjuntando el informe."

# PLANTILLAS DE clausula_aplicada
Una sola línea, técnica, ≤200 caracteres:
- Vencida/Suspendida/Cancelada: `Poliza.estado = [estado]`
- Exclusión: `Cobertura.cubierto = false (CPT [codigo], plan [plan_nombre])`
- Carencia: `Cobertura.dias_carencia = [N] (transcurridos [T] / requeridos [N])`
- Documentos: `Cobertura.documentos_requeridos no satisfechos: [lista corta]`
- Aprobación: `Cobertura aplicada: cubierto + carencia cumplida + documentacion completa`

# CIERRE
Después de emitir_decision, responde con UNA sola oración confirmando el veredicto y el decision_id retornado. Sin elaboración adicional.
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


def _run_agent_loop(
    id_informe: str, cedula: str
) -> tuple[list[dict], Optional[dict], Optional[dict], str]:
    """Ejecuta el tool-use loop. Devuelve (trace, last_submit_input,
    decision_record, final_text)."""
    decision_record: Optional[dict[str, Any]] = None
    last_submit_input: Optional[dict[str, Any]] = None
    trace: list[dict] = []
    final_text = ""

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

        for block in resp.content:
            if block.type == "text" and block.text:
                final_text = block.text

        if resp.stop_reason != "tool_use":
            break

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            input_data = dict(block.input) if isinstance(block.input, dict) else {}
            try:
                result = _dispatch(block.name, block.input)
                trace.append(
                    {"tool": block.name, "input": input_data, "output": result}
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str, ensure_ascii=False),
                    }
                )
            except Exception as exc:
                trace.append(
                    {
                        "tool": block.name,
                        "input": input_data,
                        "output": {"error": str(exc)},
                    }
                )
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

    return trace, last_submit_input, decision_record, final_text


def run_authorization(id_informe: str, cedula: str) -> AuthorizeResponse:
    _trace, last_submit_input, decision_record, _final_text = _run_agent_loop(
        id_informe, cedula
    )
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


def run_procesar(id_informe: str) -> dict:
    """Wrapper de /procesar/{id}: deriva la cedula del informe, corre el
    agente y devuelve {trace, final_text, decision} para el front."""
    informe_data = notion_service.fetch_informe(id_informe)
    paciente = informe_data.get("paciente") or {}
    cedula = paciente.get("cedula", "")
    if not cedula:
        raise AgentError(f"Informe {id_informe} no tiene paciente con cedula")

    trace, last_submit_input, _decision_record, final_text = _run_agent_loop(
        id_informe, cedula
    )

    decision_payload = None
    if last_submit_input:
        decision_payload = {
            "decision": last_submit_input["decision"],
            "justificacion": last_submit_input["justificacion"],
            "clausula_aplicada": last_submit_input.get("clausula_aplicada", "") or "",
            "documentos_faltantes": last_submit_input.get("documentos_faltantes") or [],
        }

    return {
        "trace": trace,
        "final_text": final_text,
        "decision": decision_payload,
    }
