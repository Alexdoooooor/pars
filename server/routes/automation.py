from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from server.auth_deps import require_admin
from server.db import get_connection
from server.schemas import MessageOut, ScheduleCreate, ScheduleOut, SchedulePatch

router = APIRouter(prefix="/api/automation/schedules", tags=["automation"])


def _row_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    raise TypeError("expected datetime")


@router.get("", response_model=list[ScheduleOut])
def list_schedules(_user: str = Depends(require_admin)) -> list[ScheduleOut]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sch.*, sc.title AS scenario_title
                FROM pi_schedule sch
                JOIN pi_scenario sc ON sc.id = sch.scenario_id
                ORDER BY sch.id DESC
                """
            )
            rows = cur.fetchall()
    return [
        ScheduleOut(
            id=r["id"],
            scenario_id=r["scenario_id"],
            scenario_title=r["scenario_title"] or "",
            interval_minutes=int(r["interval_minutes"]),
            enabled=bool(r["enabled"]),
            last_scheduled_run_at=_row_dt(r["last_scheduled_run_at"]) if r["last_scheduled_run_at"] else None,
            created_at=_row_dt(r["created_at"]),
        )
        for r in rows
    ]


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(body: ScheduleCreate, _user: str = Depends(require_admin)) -> ScheduleOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM pi_scenario WHERE id = %s", (body.scenario_id,))
            sc = cur.fetchone()
            if not sc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сценарий не найден")
            try:
                cur.execute(
                    """
                    INSERT INTO pi_schedule (scenario_id, interval_minutes, enabled)
                    VALUES (%s, %s, %s)
                    """,
                    (body.scenario_id, body.interval_minutes, int(body.enabled)),
                )
                sid = cur.lastrowid
            except Exception as e:
                if "Duplicate" in str(e) or "1062" in str(e):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="На этот сценарий уже есть расписание",
                    ) from e
                raise
            cur.execute(
                """
                SELECT sch.*, sc.title AS scenario_title
                FROM pi_schedule sch
                JOIN pi_scenario sc ON sc.id = sch.scenario_id
                WHERE sch.id = %s
                """,
                (sid,),
            )
            r = cur.fetchone()
    assert r is not None
    return ScheduleOut(
        id=r["id"],
        scenario_id=r["scenario_id"],
        scenario_title=r["scenario_title"] or "",
        interval_minutes=int(r["interval_minutes"]),
        enabled=bool(r["enabled"]),
        last_scheduled_run_at=_row_dt(r["last_scheduled_run_at"]) if r["last_scheduled_run_at"] else None,
        created_at=_row_dt(r["created_at"]),
    )


@router.patch("/{schedule_id}", response_model=ScheduleOut)
def patch_schedule(
    schedule_id: int,
    body: SchedulePatch,
    _user: str = Depends(require_admin),
) -> ScheduleOut:
    fields: list[str] = []
    vals: list[Any] = []
    if body.interval_minutes is not None:
        fields.append("interval_minutes = %s")
        vals.append(body.interval_minutes)
    if body.enabled is not None:
        fields.append("enabled = %s")
        vals.append(int(body.enabled))
    if not fields:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")
    vals.append(schedule_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE pi_schedule SET {', '.join(fields)} WHERE id = %s",
                tuple(vals),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            cur.execute(
                """
                SELECT sch.*, sc.title AS scenario_title
                FROM pi_schedule sch
                JOIN pi_scenario sc ON sc.id = sch.scenario_id
                WHERE sch.id = %s
                """,
                (schedule_id,),
            )
            r = cur.fetchone()
    assert r is not None
    return ScheduleOut(
        id=r["id"],
        scenario_id=r["scenario_id"],
        scenario_title=r["scenario_title"] or "",
        interval_minutes=int(r["interval_minutes"]),
        enabled=bool(r["enabled"]),
        last_scheduled_run_at=_row_dt(r["last_scheduled_run_at"]) if r["last_scheduled_run_at"] else None,
        created_at=_row_dt(r["created_at"]),
    )


@router.delete("/{schedule_id}", response_model=MessageOut)
def delete_schedule(schedule_id: int, _user: str = Depends(require_admin)) -> MessageOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pi_schedule WHERE id = %s", (schedule_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return MessageOut(message="Расписание удалено")
