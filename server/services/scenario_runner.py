from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from urllib.parse import quote_plus

from server.config import Settings, get_settings
from server.db import get_connection
from server.services.title_gen import build_scenario_title

logger = logging.getLogger(__name__)


def _mock_price_rub(scenario_id: int, platform_code: str) -> int:
    h = hashlib.sha256(f"{scenario_id}:{platform_code}".encode()).hexdigest()
    base = 35_000 + (int(h[:6], 16) % 25_000)
    if platform_code == "vtb":
        base = min(base + 800, 52_000)
    return base


def _offer_url(platform: dict[str, Any], scenario_row: dict[str, Any]) -> str:
    base = platform["base_url"].rstrip("/") + "/"
    q = quote_plus(
        f"{scenario_row.get('origin_label', '')} {scenario_row.get('destination_label', '')} "
        f"{scenario_row.get('date_departure')}"
    )
    return f"{base}?q={q}"


def execute_scenario_run(scenario_id: int, settings: Settings | None = None) -> None:
    s = settings or get_settings()
    run_id: int | None = None
    with get_connection(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM pi_scenario WHERE id = %s FOR UPDATE",
                (scenario_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            if row["status"] == "running":
                logger.info("scenario %s already running, skip duplicate run", scenario_id)
                return
            cur.execute(
                "UPDATE pi_scenario SET status = %s, last_error = NULL, updated_at = NOW(3) WHERE id = %s",
                ("running", scenario_id),
            )
            cur.execute(
                "INSERT INTO pi_run (scenario_id, status, started_at) VALUES (%s, 'running', NOW(3))",
                (scenario_id,),
            )
            run_id = cur.lastrowid

    try:
        with get_connection(s) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pi_platform ORDER BY sort_order, id")
                platforms = cur.fetchall()
                cur.execute("SELECT * FROM pi_scenario WHERE id = %s", (scenario_id,))
                scenario_row = cur.fetchone()
                if not scenario_row:
                    raise RuntimeError("Сценарий не найден")
                if run_id is None:
                    raise RuntimeError("run_id отсутствует")

                remote_by_code: dict[str, dict[str, Any]] | None = None
                if (s.parser_service_url or "").strip():
                    from server.services.parser_client import fetch_parse_by_platform_code

                    remote_by_code = fetch_parse_by_platform_code(scenario_row, scenario_id, s)

                for p in platforms:
                    err: str | None = None
                    price_kopecks: int | None = None
                    url: str | None = None
                    meta: dict[str, Any] = {"mode": s.parser_mode, "source": "local"}

                    if remote_by_code is not None:
                        meta["source"] = "parser_service"
                        item = remote_by_code.get(p["code"])
                        if not item:
                            err = "Площадка отсутствует в ответе парсер-сервиса"
                        else:
                            meta.update(item.get("meta") or {})
                            err = item.get("error")
                            url = item.get("offer_url")
                            pr = item.get("price_rub")
                            if pr is not None and err is None:
                                price_kopecks = int(round(float(pr) * 100))
                    elif s.parser_mode == "mock":
                        rub = _mock_price_rub(scenario_id, p["code"])
                        price_kopecks = rub * 100
                        url = _offer_url(p, scenario_row)
                    else:
                        err = "Задайте PARSER_SERVICE_URL или PARSER_MODE=mock."
                        meta["todo"] = "Подключить парсер-сервис или mock."

                    cur.execute(
                        """
                        INSERT INTO pi_result (run_id, platform_id, price_kopecks, currency, offer_url, error_text, raw_meta)
                        VALUES (%s, %s, %s, 'RUB', %s, %s, %s)
                        """,
                        (
                            run_id,
                            p["id"],
                            price_kopecks,
                            url,
                            err,
                            json.dumps(meta, ensure_ascii=False),
                        ),
                    )

                cur.execute(
                    "UPDATE pi_run SET status = 'success', finished_at = NOW(3) WHERE id = %s",
                    (run_id,),
                )
                cur.execute(
                    "UPDATE pi_scenario SET status = 'success', last_error = NULL, updated_at = NOW(3) WHERE id = %s",
                    (scenario_id,),
                )
    except Exception as e:
        logger.exception("run failed scenario_id=%s run_id=%s", scenario_id, run_id)
        err_msg = str(e)
        with get_connection(s) as conn:
            with conn.cursor() as cur:
                if run_id is not None:
                    cur.execute(
                        "UPDATE pi_run SET status = 'error', finished_at = NOW(3) WHERE id = %s",
                        (run_id,),
                    )
                cur.execute(
                    "UPDATE pi_scenario SET status = 'error', last_error = %s, updated_at = NOW(3) WHERE id = %s",
                    (err_msg[:2000], scenario_id),
                )


def refresh_scenario_title(scenario_id: int, settings: Settings | None = None) -> None:
    s = settings or get_settings()
    with get_connection(s) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pi_scenario WHERE id = %s", (scenario_id,))
            row = cur.fetchone()
            if not row:
                return
            title = build_scenario_title(
                row["origin_label"] or "",
                row["destination_label"] or "",
                row["date_departure"],
                row["date_return"],
                row["time_departure_pref"],
                row["time_return_pref"],
                row["product_type"],
            )
            cur.execute(
                "UPDATE pi_scenario SET title = %s, updated_at = NOW(3) WHERE id = %s",
                (title, scenario_id),
            )
