from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class ScenarioPayload(BaseModel):
    """Вход парсера — тот же смысл, что и сценарий в Price Intelligence."""

    scenario_id: int = Field(..., ge=1, description="ID сценария в основной БД (для mock-детерминизма)")
    product_type: str = "avia"
    origin_label: str = ""
    origin_code: str = ""
    destination_label: str = ""
    destination_code: str = ""
    date_departure: date
    date_return: date | None = None
    time_departure_pref: str | None = None
    time_return_pref: str | None = None
    passengers_adults: int = Field(default=1, ge=1, le=9)
    cabin_class: str = "economy"
    direct_only: bool = False
    baggage_included: bool = False
    tariff_notes: str | None = None


class PlatformResultOut(BaseModel):
    platform_code: str
    display_name: str
    price_rub: float | None = None
    offer_url: str | None = None
    error: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ParseResponse(BaseModel):
    ok: bool
    mode: str
    results: list[PlatformResultOut]
    detail: str | None = None


class HealthOut(BaseModel):
    service: str
    ok: bool
    parser_mode: str
    api_key_configured: bool
