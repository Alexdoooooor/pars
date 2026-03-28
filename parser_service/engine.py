from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import quote_plus

from parser_service.adapters.http_live import probe_platform_http
from parser_service.platforms_data import PLATFORMS
from parser_service.schemas import ParseResponse, PlatformResultOut, ScenarioPayload

logger = logging.getLogger(__name__)


def _mock_price_rub(scenario_id: int, platform_code: str) -> int:
    h = hashlib.sha256(f"{scenario_id}:{platform_code}".encode()).hexdigest()
    base = 35_000 + (int(h[:6], 16) % 25_000)
    if platform_code == "vtb":
        base = min(base + 800, 52_000)
    return base


def _offer_url(base_url: str, payload: ScenarioPayload) -> str:
    base = base_url.rstrip("/") + "/"
    q = quote_plus(
        f"{payload.origin_label} {payload.destination_label} {payload.date_departure.isoformat()}"
    )
    return f"{base}?q={q}"


def run_parse(payload: ScenarioPayload, mode: str) -> ParseResponse:
    mode_l = (mode or "mock").strip().lower()
    results: list[PlatformResultOut] = []
    live_modes = {"live", "http", "real"}

    for p in sorted(PLATFORMS, key=lambda x: x["sort_order"]):
        code = p["code"]
        meta: dict[str, Any] = {"mode": mode_l}
        err: str | None = None
        price_rub: float | None = None
        url: str | None = None

        if mode_l == "mock":
            rub = _mock_price_rub(payload.scenario_id, code)
            price_rub = float(rub)
            url = _offer_url(p["base_url"], payload)
        elif mode_l in live_modes:
            probe = probe_platform_http(p, payload)
            price_rub = probe.price_rub
            url = probe.offer_url
            err = probe.error
            meta.update(probe.meta)
        else:
            err = (
                f"Режим «{mode_l}» не реализован в сервисе парсера. "
                "Используйте PARSER_MODE=mock или PARSER_MODE=live."
            )
            meta["supported_modes"] = ["mock", "live"]

        results.append(
            PlatformResultOut(
                platform_code=code,
                display_name=p["display_name"],
                price_rub=price_rub,
                offer_url=url,
                error=err,
                meta=meta,
            )
        )

    return ParseResponse(ok=True, mode=mode_l, results=results, detail=None)
