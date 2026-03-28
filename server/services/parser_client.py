from __future__ import annotations

import logging
from typing import Any

import httpx

from server.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _scenario_to_payload(scenario_row: dict[str, Any], scenario_id: int) -> dict[str, Any]:
    dr = scenario_row["date_return"]
    return {
        "scenario_id": scenario_id,
        "product_type": scenario_row.get("product_type") or "avia",
        "origin_label": scenario_row.get("origin_label") or "",
        "origin_code": scenario_row.get("origin_code") or "",
        "destination_label": scenario_row.get("destination_label") or "",
        "destination_code": scenario_row.get("destination_code") or "",
        "date_departure": scenario_row["date_departure"].isoformat()
        if hasattr(scenario_row["date_departure"], "isoformat")
        else str(scenario_row["date_departure"]),
        "date_return": dr.isoformat() if dr and hasattr(dr, "isoformat") else (str(dr) if dr else None),
        "time_departure_pref": scenario_row.get("time_departure_pref"),
        "time_return_pref": scenario_row.get("time_return_pref"),
        "passengers_adults": int(scenario_row.get("passengers_adults") or 1),
        "cabin_class": scenario_row.get("cabin_class") or "economy",
        "direct_only": bool(scenario_row.get("direct_only")),
        "baggage_included": bool(scenario_row.get("baggage_included")),
        "tariff_notes": scenario_row.get("tariff_notes"),
    }


def fetch_parse_by_platform_code(
    scenario_row: dict[str, Any],
    scenario_id: int,
    settings: Settings | None = None,
) -> dict[str, dict[str, Any]]:
    s = settings or get_settings()
    base = (s.parser_service_url or "").strip().rstrip("/")
    key = (s.parser_service_api_key or "").strip()
    if not base:
        raise RuntimeError("PARSER_SERVICE_URL не задан")
    if not key:
        raise RuntimeError("PARSER_SERVICE_API_KEY не задан")

    url = f"{base}/v1/parse"
    payload = _scenario_to_payload(scenario_row, scenario_id)
    headers = {"X-Parser-Api-Key": key, "Content-Type": "application/json"}
    timeout = httpx.Timeout(s.parser_service_timeout)

    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload, headers=headers)
        if r.status_code == 401:
            raise RuntimeError("Парсер API: 401 — проверьте PARSER_SERVICE_API_KEY")
        r.raise_for_status()
        data = r.json()

    if not data.get("ok"):
        raise RuntimeError(data.get("detail") or "Парсер вернул ok=false")

    out: dict[str, dict[str, Any]] = {}
    for item in data.get("results") or []:
        code = item.get("platform_code")
        if code:
            out[str(code)] = item
    return out
