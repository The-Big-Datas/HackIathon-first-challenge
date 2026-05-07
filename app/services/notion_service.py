from datetime import date, datetime
from typing import Any

from notion_client import AsyncClient

from app.config import get_settings
from app.models.schemas import AuthorizationDecision, InsurancePolicy, MedicalReport


def _plain_text(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    rich = prop.get("rich_text") or prop.get("title") or []
    return "".join(part.get("plain_text", "") for part in rich)


def _select(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    sel = prop.get("select") or {}
    return sel.get("name", "")


def _multi_select(prop: dict[str, Any] | None) -> list[str]:
    if not prop:
        return []
    return [item.get("name", "") for item in prop.get("multi_select", [])]


def _number(prop: dict[str, Any] | None, default: float = 0.0) -> float:
    if not prop:
        return default
    val = prop.get("number")
    return float(val) if val is not None else default


def _date(prop: dict[str, Any] | None) -> date | None:
    if not prop:
        return None
    d = prop.get("date") or {}
    raw = d.get("start")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _files(prop: dict[str, Any] | None) -> list[str]:
    if not prop:
        return []
    out: list[str] = []
    for f in prop.get("files", []):
        if f.get("type") == "external":
            out.append(f.get("external", {}).get("url", ""))
        elif f.get("type") == "file":
            out.append(f.get("file", {}).get("url", ""))
    return [u for u in out if u]


class NotionService:
    """Cliente para leer/escribir registros de Notion (informes, pólizas, decisiones)."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncClient(auth=settings.notion_api_key)
        self.reports_db = settings.notion_medical_reports_db_id
        self.policies_db = settings.notion_policies_db_id
        self.decisions_db = settings.notion_decisions_db_id

    async def get_medical_report(self, report_id: str) -> MedicalReport | None:
        response = await self.client.databases.query(
            database_id=self.reports_db,
            filter={"property": "report_id", "rich_text": {"equals": report_id}},
            page_size=1,
        )
        results = response.get("results", [])
        if not results:
            return None
        page = results[0]
        props = page.get("properties", {})
        return MedicalReport(
            report_id=_plain_text(props.get("report_id")) or report_id,
            patient_id=_plain_text(props.get("patient_id")),
            patient_name=_plain_text(props.get("patient_name")),
            diagnosis=_plain_text(props.get("diagnosis")),
            procedure_code=_plain_text(props.get("procedure_code")),
            procedure_name=_plain_text(props.get("procedure_name")),
            requested_date=_date(props.get("requested_date")) or date.today(),
            attending_physician=_plain_text(props.get("attending_physician")),
            clinical_notes=_plain_text(props.get("clinical_notes")) or None,
            attachments=_files(props.get("attachments")),
        )

    async def get_policy_for_patient(self, patient_id: str) -> InsurancePolicy | None:
        response = await self.client.databases.query(
            database_id=self.policies_db,
            filter={"property": "patient_id", "rich_text": {"equals": patient_id}},
            page_size=1,
        )
        results = response.get("results", [])
        if not results:
            return None
        page = results[0]
        props = page.get("properties", {})

        waiting_raw = _plain_text(props.get("waiting_periods_months"))
        waiting: dict[str, int] = {}
        for item in waiting_raw.split(","):
            if ":" in item:
                k, v = item.split(":", 1)
                try:
                    waiting[k.strip()] = int(v.strip())
                except ValueError:
                    pass

        return InsurancePolicy(
            policy_id=_plain_text(props.get("policy_id")),
            patient_id=_plain_text(props.get("patient_id")) or patient_id,
            plan_name=_plain_text(props.get("plan_name")),
            effective_date=_date(props.get("effective_date")) or date.today(),
            expiration_date=_date(props.get("expiration_date")) or date.today(),
            covered_procedures=_multi_select(props.get("covered_procedures")),
            excluded_procedures=_multi_select(props.get("excluded_procedures")),
            waiting_periods_months=waiting,
            deductible=_number(props.get("deductible")),
            coverage_percentage=_number(props.get("coverage_percentage"), default=100.0),
            status=(_select(props.get("status")) or "active").lower(),  # type: ignore[arg-type]
        )

    async def save_decision(self, decision: AuthorizationDecision) -> str | None:
        if not self.decisions_db:
            return None
        page = await self.client.pages.create(
            parent={"database_id": self.decisions_db},
            properties={
                "report_id": {"title": [{"text": {"content": decision.report_id}}]},
                "patient_id": {"rich_text": [{"text": {"content": decision.patient_id}}]},
                "decision": {"select": {"name": decision.decision}},
                "rationale": {"rich_text": [{"text": {"content": decision.rationale[:1900]}}]},
                "missing_documents": {
                    "multi_select": [{"name": d[:99]} for d in decision.missing_documents]
                },
                "issued_at": {"date": {"start": decision.issued_at}},
            },
        )
        return page.get("id")

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"
