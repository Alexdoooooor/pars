from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from server.auth_deps import require_admin
from server.db import get_connection
from server.schemas import (
    MessageOut,
    PlatformOut,
    ProductType,
    ResultOut,
    RunOut,
    RunStatus,
    ScenarioCreate,
    ScenarioListItem,
    ScenarioOut,
    ScenarioStatus,
)
from server.services.scenario_runner import execute_scenario_run, refresh_scenario_title
from server.services.title_gen import build_scenario_title

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def _row_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v
    raise TypeError("expected datetime")


def _row_date(v: Any) -> date:
    if isinstance(v, date):
        return v
    raise TypeError("expected date")


@router.get("", response_model=list[ScenarioListItem])
def list_scenarios(_user: str = Depends(require_admin)) -> list[ScenarioListItem]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.*, lr.status AS latest_run_status, lr.finished_at AS latest_run_finished_at
                FROM pi_scenario s
                LEFT JOIN pi_run lr ON lr.id = (
                  SELECT id FROM pi_run WHERE scenario_id = s.id ORDER BY id DESC LIMIT 1
                )
                ORDER BY s.id DESC
                """
            )
            rows = cur.fetchall()
    out: list[ScenarioListItem] = []
    for r in rows:
        lrs = r.get("latest_run_status")
        lrf = r.get("latest_run_finished_at")
        out.append(
            ScenarioListItem(
                id=r["id"],
                title=r["title"],
                product_type=ProductType(r["product_type"]),
                status=ScenarioStatus(r["status"]),
                created_at=_row_dt(r["created_at"]),
                updated_at=_row_dt(r["updated_at"]),
                latest_run_status=RunStatus(lrs) if lrs else None,
                latest_run_finished_at=_row_dt(lrf) if lrf else None,
            )
        )
    return out


def _load_latest_run(cur: Any, scenario_id: int) -> RunOut | None:
    cur.execute(
        "SELECT * FROM pi_run WHERE scenario_id = %s ORDER BY id DESC LIMIT 1",
        (scenario_id,),
    )
    run = cur.fetchone()
    if not run:
        return None
    cur.execute(
        """
        SELECT res.*, p.id AS p_id, p.code AS p_code, p.display_name AS p_display_name,
               p.base_url AS p_base_url, p.sort_order AS p_sort_order
        FROM pi_result res
        JOIN pi_platform p ON p.id = res.platform_id
        WHERE res.run_id = %s
        ORDER BY p.sort_order, p.id
        """,
        (run["id"],),
    )
    res_rows = cur.fetchall()
    results: list[ResultOut] = []
    for x in res_rows:
        rub: float | None = None
        if x["price_kopecks"] is not None:
            rub = round(x["price_kopecks"] / 100.0, 2)
        results.append(
            ResultOut(
                platform=PlatformOut(
                    id=x["p_id"],
                    code=x["p_code"],
                    display_name=x["p_display_name"],
                    base_url=x["p_base_url"],
                    sort_order=x["p_sort_order"],
                ),
                price_rub=rub,
                offer_url=x["offer_url"],
                error_text=x["error_text"],
            )
        )
    fin = run["finished_at"]
    return RunOut(
        id=run["id"],
        status=RunStatus(run["status"]),
        started_at=_row_dt(run["started_at"]),
        finished_at=_row_dt(fin) if fin else None,
        results=results,
    )


@router.get("/{scenario_id}", response_model=ScenarioOut)
def get_scenario(scenario_id: int, _user: str = Depends(require_admin)) -> ScenarioOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM pi_scenario WHERE id = %s", (scenario_id,))
            r = cur.fetchone()
            if not r:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            latest = _load_latest_run(cur, scenario_id)
    return ScenarioOut(
        id=r["id"],
        title=r["title"],
        product_type=ProductType(r["product_type"]),
        origin_label=r["origin_label"] or "",
        origin_code=r["origin_code"] or "",
        destination_label=r["destination_label"] or "",
        destination_code=r["destination_code"] or "",
        date_departure=_row_date(r["date_departure"]),
        date_return=_row_date(r["date_return"]) if r["date_return"] else None,
        time_departure_pref=r["time_departure_pref"],
        time_return_pref=r["time_return_pref"],
        passengers_adults=int(r["passengers_adults"]),
        cabin_class=r["cabin_class"] or "economy",
        direct_only=bool(r["direct_only"]),
        baggage_included=bool(r["baggage_included"]),
        tariff_notes=r["tariff_notes"],
        status=ScenarioStatus(r["status"]),
        last_error=r["last_error"],
        created_at=_row_dt(r["created_at"]),
        updated_at=_row_dt(r["updated_at"]),
        latest_run=latest,
    )


@router.post("", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
def create_scenario(body: ScenarioCreate, _user: str = Depends(require_admin)) -> ScenarioOut:
    title = build_scenario_title(
        body.origin_label,
        body.destination_label,
        body.date_departure,
        body.date_return,
        body.time_departure_pref,
        body.time_return_pref,
        body.product_type.value,
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pi_scenario (
                  title, product_type, origin_label, origin_code, destination_label, destination_code,
                  date_departure, date_return, time_departure_pref, time_return_pref,
                  passengers_adults, cabin_class, direct_only, baggage_included, tariff_notes, status
                ) VALUES (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft'
                )
                """,
                (
                    title,
                    body.product_type.value,
                    body.origin_label,
                    body.origin_code,
                    body.destination_label,
                    body.destination_code,
                    body.date_departure,
                    body.date_return,
                    body.time_departure_pref,
                    body.time_return_pref,
                    body.passengers_adults,
                    body.cabin_class,
                    int(body.direct_only),
                    int(body.baggage_included),
                    body.tariff_notes,
                ),
            )
            sid = cur.lastrowid
    return get_scenario(sid, _user)


@router.delete("/{scenario_id}", response_model=MessageOut)
def delete_scenario(scenario_id: int, _user: str = Depends(require_admin)) -> MessageOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pi_scenario WHERE id = %s", (scenario_id,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return MessageOut(message="Удалено", scenario_id=scenario_id)


@router.post("/{scenario_id}/run", response_model=MessageOut)
def queue_run(
    scenario_id: int,
    background_tasks: BackgroundTasks,
    _user: str = Depends(require_admin),
) -> MessageOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM pi_scenario WHERE id = %s", (scenario_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    background_tasks.add_task(execute_scenario_run, scenario_id)
    return MessageOut(message="Добавлено в обработку", scenario_id=scenario_id)


@router.post("/{scenario_id}/refresh-title", response_model=MessageOut)
def refresh_title(scenario_id: int, _user: str = Depends(require_admin)) -> MessageOut:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM pi_scenario WHERE id = %s", (scenario_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    refresh_scenario_title(scenario_id)
    return MessageOut(message="Название обновлено", scenario_id=scenario_id)
