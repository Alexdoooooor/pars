from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pymysql
from pymysql.cursors import DictCursor

from server.config import Settings, get_settings


def _connect_kwargs(s: Settings) -> dict[str, Any]:
    if s.db_socket:
        return {
            "unix_socket": s.db_socket,
            "user": s.db_user,
            "password": s.db_password,
            "database": s.pi_db_name,
            "charset": "utf8mb4",
            "cursorclass": DictCursor,
            "autocommit": False,
        }
    return {
        "host": s.db_host,
        "port": s.db_port,
        "user": s.db_user,
        "password": s.db_password,
        "database": s.pi_db_name,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }


@contextmanager
def get_connection(settings: Settings | None = None) -> Iterator[pymysql.connections.Connection]:
    s = settings or get_settings()
    conn = pymysql.connect(**_connect_kwargs(s))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
