from __future__ import annotations

from fastapi import APIRouter, Depends

from server.auth_deps import require_admin
from server.config import get_settings
from server.db import get_connection
from server.schemas import AnalyticsSummaryOut

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryOut)
def analytics_summary(_user: str = Depends(require_admin)) -> AnalyticsSummaryOut:
    s = get_settings()
    with get_connection(s) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM pi_scenario")
            scenarios_total = int(cur.fetchone()["c"])
            cur.execute("SELECT COUNT(*) AS c FROM pi_run")
            runs_total = int(cur.fetchone()["c"])
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM pi_run
                WHERE started_at >= (NOW(3) - INTERVAL 1 DAY)
                """
            )
            runs_last_24h = int(cur.fetchone()["c"])
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM pi_run
                WHERE started_at >= (NOW(3) - INTERVAL 1 DAY) AND status = 'success'
                """
            )
            runs_success_last_24h = int(cur.fetchone()["c"])
            cur.execute(
                """
                SELECT COUNT(*) AS c FROM pi_run
                WHERE started_at >= (NOW(3) - INTERVAL 1 DAY) AND status = 'error'
                """
            )
            runs_error_last_24h = int(cur.fetchone()["c"])
            cur.execute("SELECT status, COUNT(*) AS c FROM pi_scenario GROUP BY status")
            by_status: dict[str, int] = {}
            for row in cur.fetchall():
                by_status[str(row["status"])] = int(row["c"])
    return AnalyticsSummaryOut(
        scenarios_total=scenarios_total,
        runs_total=runs_total,
        runs_last_24h=runs_last_24h,
        runs_success_last_24h=runs_success_last_24h,
        runs_error_last_24h=runs_error_last_24h,
        scenarios_by_status=by_status,
        parser_mode=s.parser_mode,
    )
