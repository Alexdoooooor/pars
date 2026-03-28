"""
Apply sql/schema.sql to an existing remote MySQL database.

Usage (PowerShell example):
  $env:DB_HOST="..."
  $env:DB_PORT="3306"
  $env:DB_NAME="..."
  $env:DB_USER="..."
  $env:DB_PASSWORD="..."
  python scripts/apply_schema_remote.py
"""
from __future__ import annotations

import os
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"


def split_sql(sql_text: str) -> list[str]:
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


def main() -> None:
    host = os.getenv("DB_HOST", "").strip()
    port = int(os.getenv("DB_PORT", "3306").strip())
    db_name = os.getenv("DB_NAME", "").strip()
    user = os.getenv("DB_USER", "").strip()
    password = os.getenv("DB_PASSWORD", "")

    missing = [k for k, v in {
        "DB_HOST": host,
        "DB_NAME": db_name,
        "DB_USER": user,
        "DB_PASSWORD": password,
    }.items() if not v]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")

    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Schema file not found: {SCHEMA_PATH}")

    schema_text = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = split_sql(schema_text)

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db_name,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        for stmt in statements:
            up = stmt.upper()
            if up.startswith("CREATE DATABASE") or up.startswith("USE "):
                continue
            with conn.cursor() as cur:
                cur.execute(stmt)
        conn.commit()
        print(f"OK: schema applied to `{db_name}` at {host}:{port}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
