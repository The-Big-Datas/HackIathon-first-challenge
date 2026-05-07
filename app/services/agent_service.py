import json
import os
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

from app.config import get_settings
from app.models.schemas import AuthorizationDecision
from app.services.notion_service import NotionService

SYSTEM_PROMPT = """Eres un agente de pre-autorización médica para una aseguradora.

Tu objetivo: analizar de forma instantánea si un procedimiento quirúrgico solicitado
por un hospital puede ser pre-aprobado según la póliza del paciente.

Procedimiento de trabajo (DEBES seguirlo en este orden):
1. Llama a `fetch_medical_report` con el `report_id` recibido para obtener el informe del hospital.
2. Llama a `fetch_policy` con el `patient_id` para obtener la póliza vigente.
3. Analiza:
   - Vigencia de la póliza (status == "active" y la fecha de hoy entre effective_date y expiration_date).
   - Cobertura: el `procedure_code` o `procedure_name` debe estar en `covered_procedures`
     y NO en `excluded_procedures`.
   - Carencia (waiting period): calcula los meses transcurridos desde `effective_date`
     hasta `requested_date`. Si el procedimiento aparece en `waiting_periods_months`
     y los meses transcurridos son menores al requerido, NO se cumple la carencia.
   - Documentos faltantes: si el informe no tiene `clinical_notes` o `attachments`
     y el procedimiento es de alto costo, solicita los documentos.
4. Llama a `submit_decision` con UNA de estas decisiones:
   - "pre_approved": cumple todo.
   - "missing_documents": falta documentación; lista los documentos requeridos.
   - "rejected": exclusión explícita, póliza inactiva o carencia incumplida.
   - "needs_review": casos ambiguos que requieren revisión humana.

Sé conciso, fundamenta tu razonamiento en datos concretos de la póliza y el informe.
Responde siempre en español."""


def _build_tools(notion: NotionService, ctx: dict[str, Any]):
    @tool(
        "fetch_medical_report",
        "Obtiene el informe médico digital desde Notion usando el report_id.",
        {"report_id": str},
    )
    async def fetch_medical_report(args: dict[str, Any]) -> dict[str, Any]:
        report = await notion.get_medical_report(args["report_id"])
        if not report:
            return {
                "content": [
                    {"type": "text", "text": f"No se encontró el informe {args['report_id']}."}
                ],
                "isError": True,
            }
        ctx["report"] = report
        return {
            "content": [
                {"type": "text", "text": report.model_dump_json(indent=2)}
            ]
        }

    @tool(
        "fetch_policy",
        "Obtiene la póliza vigente del paciente desde Notion usando el patient_id.",
        {"patient_id": str},
    )
    async def fetch_policy(args: dict[str, Any]) -> dict[str, Any]:
        policy = await notion.get_policy_for_patient(args["patient_id"])
        if not policy:
            return {
                "content": [
                    {"type": "text", "text": f"No se encontró póliza para el paciente {args['patient_id']}."}
                ],
                "isError": True,
            }
        ctx["policy"] = policy
        return {
            "content": [
                {"type": "text", "text": policy.model_dump_json(indent=2)}
            ]
        }

    @tool(
        "submit_decision",
        "Registra la decisión final de pre-autorización en Notion.",
        {
            "decision": str,
            "rationale": str,
            "missing_documents": list,
            "coverage_percentage": float,
            "estimated_patient_cost": float,
        },
    )
    async def submit_decision(args: dict[str, Any]) -> dict[str, Any]:
        report = ctx.get("report")
        if not report:
            return {
                "content": [{"type": "text", "text": "Primero llama a fetch_medical_report."}],
                "isError": True,
            }
        decision = AuthorizationDecision(
            report_id=report.report_id,
            patient_id=report.patient_id,
            decision=args["decision"],  # type: ignore[arg-type]
            rationale=args["rationale"],
            missing_documents=args.get("missing_documents") or [],
            coverage_percentage=args.get("coverage_percentage"),
            estimated_patient_cost=args.get("estimated_patient_cost"),
            issued_at=NotionService.now_iso(),
        )
        ctx["decision"] = decision
        await notion.save_decision(decision)
        return {
            "content": [
                {"type": "text", "text": f"Decisión registrada: {decision.decision}"}
            ]
        }

    return [fetch_medical_report, fetch_policy, submit_decision]


class PreAuthorizationAgent:
    """Orquesta la conversación con Claude para emitir una pre-autorización."""

    def __init__(self) -> None:
        settings = get_settings()
        os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key)
        self.notion = NotionService()

    async def run(self, report_id: str, patient_id: str) -> AuthorizationDecision:
        ctx: dict[str, Any] = {}
        tools = _build_tools(self.notion, ctx)
        mcp_server = create_sdk_mcp_server(name="preauth-tools", version="1.0.0", tools=tools)

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"preauth": mcp_server},
            allowed_tools=[
                "mcp__preauth__fetch_medical_report",
                "mcp__preauth__fetch_policy",
                "mcp__preauth__submit_decision",
            ],
            max_turns=8,
            permission_mode="acceptEdits",
        )

        user_prompt = (
            f"Procesa la solicitud de pre-autorización con report_id='{report_id}' "
            f"y patient_id='{patient_id}'. Sigue el procedimiento y termina llamando "
            f"a submit_decision."
        )

        transcript: list[str] = []
        async with ClaudeSDKClient(options=options) as client:
            await client.query(user_prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            transcript.append(block.text)

        decision = ctx.get("decision")
        if not decision:
            return AuthorizationDecision(
                report_id=report_id,
                patient_id=patient_id,
                decision="needs_review",
                rationale="El agente no emitió una decisión. Transcripción: "
                + " | ".join(transcript)[:1500],
                issued_at=NotionService.now_iso(),
            )
        return decision
