"""Carga de variables de entorno desde backend/.env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


def _required(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Falta variable de entorno {name}. Revisa backend/.env "
            f"(ver docs/notion_setup.md)."
        )
    return val


class Settings:
    ANTHROPIC_API_KEY: str = _required("ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

    NOTION_TOKEN: str = _required("NOTION_TOKEN")
    NOTION_DB_ASEGURADOS: str = _required("NOTION_DB_ASEGURADOS")
    NOTION_DB_POLIZAS: str = _required("NOTION_DB_POLIZAS")
    NOTION_DB_PLANES: str = _required("NOTION_DB_PLANES")
    NOTION_DB_COBERTURAS: str = _required("NOTION_DB_COBERTURAS")
    NOTION_DB_INFORMES: str = _required("NOTION_DB_INFORMES")
    NOTION_DB_DECISIONES: str = _required("NOTION_DB_DECISIONES")


settings = Settings()
