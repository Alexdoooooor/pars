from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote_plus

import httpx

from parser_service.platforms_data import PlatformDef
from parser_service.schemas import ScenarioPayload

_PRICE_RE = re.compile(
    r"(?P<num>\d{1,3}(?:[ \u00A0]\d{3})+|\d{4,7})\s*(?:₽|руб(?:\.|ля|лей)?)",
    flags=re.IGNORECASE,
)


@dataclass
class LiveProbeResult:
    price_rub: float | None
    offer_url: str
    error: str | None
    meta: dict[str, Any]


def _build_offer_url(base_url: str, payload: ScenarioPayload) -> str:
    base = base_url.rstrip("/") + "/"
    q = quote_plus(
        f"{payload.origin_label} {payload.destination_label} {payload.date_departure.isoformat()}"
    )
    return f"{base}?q={q}"


def _extract_prices_rub(text: str) -> list[int]:
    values: list[int] = []
    for match in _PRICE_RE.finditer(text):
        num = match.group("num").replace(" ", "").replace("\u00A0", "")
        try:
            parsed = int(num)
        except ValueError:
            continue
        # Фильтр мусора: исключаем слишком маленькие и аномально большие числа.
        if 500 <= parsed <= 5_000_000:
            values.append(parsed)
    return values


def probe_platform_http(
    platform: PlatformDef,
    payload: ScenarioPayload,
    *,
    timeout_sec: float = 15.0,
) -> LiveProbeResult:
    request_url = _build_offer_url(platform["base_url"], payload)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(timeout_sec), follow_redirects=True) as client:
            response = client.get(request_url, headers=headers)
            status_code = response.status_code
            final_url = str(response.url)
            text = response.text
    except Exception as exc:
        return LiveProbeResult(
            price_rub=None,
            offer_url=request_url,
            error=f"http error: {exc}",
            meta={"adapter": "http_live", "stage": "request"},
        )

    if status_code >= 400:
        return LiveProbeResult(
            price_rub=None,
            offer_url=final_url,
            error=f"http status {status_code}",
            meta={"adapter": "http_live", "status_code": status_code},
        )

    prices = _extract_prices_rub(text)
    if not prices:
        return LiveProbeResult(
            price_rub=None,
            offer_url=final_url,
            error="price not found in html",
            meta={
                "adapter": "http_live",
                "status_code": status_code,
                "content_length": len(text),
                "candidates": 0,
            },
        )

    best = min(prices)
    return LiveProbeResult(
        price_rub=float(best),
        offer_url=final_url,
        error=None,
        meta={
            "adapter": "http_live",
            "status_code": status_code,
            "content_length": len(text),
            "candidates": len(prices),
            "sample_min_rub": best,
        },
    )
