from __future__ import annotations

import logging
from pathlib import Path

from server.config import get_settings
from server.db import get_connection

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"


def _split_sql(sql_text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for line in sql_text.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    if buf:
        parts.append("\n".join(buf))
    return parts


def ensure_schema_applied() -> None:
    settings = get_settings()
    if not settings.db_user:
        logger.warning("DB_USER is empty, skip schema bootstrap")
        return
    if not SCHEMA_PATH.exists():
        logger.warning("schema file not found at %s", SCHEMA_PATH)
        return

    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = _split_sql(schema_text)

    with get_connection(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(f"USE `{settings.pi_db_name}`")
        for stmt in statements:
            up = stmt.upper()
            if up.startswith("CREATE DATABASE") or up.startswith("USE "):
                continue
            with conn.cursor() as cur:
                cur.execute(f"USE `{settings.pi_db_name}`")
                cur.execute(stmt)
    logger.info("schema bootstrap complete for database `%s`", settings.pi_db_name)
