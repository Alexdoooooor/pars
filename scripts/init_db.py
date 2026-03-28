"""
Создаёт базу PI_DB_NAME и применяет sql/schema.sql.
Запуск из корня проекта: python scripts/init_db.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymysql

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from server.config import get_settings  # noqa: E402


def _split_sql(sql_text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for line in sql_text.splitlines():
        s = line.strip()
        if s.startswith("--") or not s:
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    if buf:
        parts.append("\n".join(buf))
    return parts


def main() -> None:
    s = get_settings()
    if not s.db_user:
        raise SystemExit("Заполните DB_USER и DB_PASSWORD в .env")
    if s.db_socket:
        conn = pymysql.connect(
            unix_socket=s.db_socket,
            user=s.db_user,
            password=s.db_password,
            charset="utf8mb4",
        )
    else:
        conn = pymysql.connect(
            host=s.db_host,
            port=s.db_port,
            user=s.db_user,
            password=s.db_password,
            charset="utf8mb4",
        )
    db_name = re.sub(r"[^a-zA-Z0-9_]", "", s.pi_db_name)
    if db_name != s.pi_db_name:
        raise SystemExit("Некорректное PI_DB_NAME")
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            except pymysql.err.OperationalError as e:
                # На shared-хостингах часто нет прав CREATE DATABASE.
                # Если БД уже создана в панели, продолжаем и просто используем её.
                if e.args and int(e.args[0]) == 1044:
                    print(
                        f"INFO: нет прав CREATE DATABASE для `{db_name}`; "
                        "продолжаю с существующей БД."
                    )
                else:
                    raise
            cur.execute(f"USE `{db_name}`")
        schema_path = _ROOT / "sql" / "schema.sql"
        text = schema_path.read_text(encoding="utf-8")
        for stmt in _split_sql(text):
            if stmt.upper().startswith("CREATE DATABASE"):
                continue
            if stmt.upper().startswith("USE "):
                continue
            with conn.cursor() as cur:
                cur.execute(f"USE `{db_name}`")
                cur.execute(stmt)
        conn.commit()
        print(f"OK: база `{db_name}` и таблицы pi_* готовы.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
