from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from server.config import get_settings
from server.db import get_connection
from server.services.scenario_runner import execute_scenario_run

logger = logging.getLogger(__name__)


def _due_schedule_ids() -> list[tuple[int, int]]:
    """Возвращает [(schedule_id, scenario_id), ...] для прогонов по расписанию."""
    s = get_settings()
    out: list[tuple[int, int]] = []
    with get_connection(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sch.id, sch.scenario_id, sch.interval_minutes, sch.last_scheduled_run_at, sc.status
                FROM pi_schedule sch
                JOIN pi_scenario sc ON sc.id = sch.scenario_id
                WHERE sch.enabled = 1
                """
            )
            rows = cur.fetchall()
            for r in rows:
                if r["status"] == "running":
                    continue
                last = r["last_scheduled_run_at"]
                interval = max(1, int(r["interval_minutes"]))
                if last is None:
                    out.append((r["id"], r["scenario_id"]))
                    continue
                cur.execute(
                    "SELECT TIMESTAMPDIFF(MINUTE, %s, NOW(3)) AS diff",
                    (last,),
                )
                diff_row = cur.fetchone()
                diff = int(diff_row["diff"]) if diff_row and diff_row["diff"] is not None else interval
                if diff >= interval:
                    out.append((r["id"], r["scenario_id"]))
    return out


def _mark_schedule_started(schedule_id: int) -> None:
    s = get_settings()
    with get_connection(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pi_schedule SET last_scheduled_run_at = NOW(3) WHERE id = %s",
                (schedule_id,),
            )


def run_due_schedules_sync() -> None:
    for schedule_id, scenario_id in _due_schedule_ids():
        try:
            _mark_schedule_started(schedule_id)
            execute_scenario_run(scenario_id)
        except Exception:
            logger.exception("scheduled run failed schedule_id=%s scenario_id=%s", schedule_id, scenario_id)


async def scheduler_loop() -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.to_thread(run_due_schedules_sync)
        except Exception:
            logger.exception("scheduler tick failed")
        await asyncio.sleep(60)
