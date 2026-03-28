from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProductType(str, Enum):
    avia = "avia"
    rail = "rail"
    hotel = "hotel"


class ScenarioStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    running = "running"
    success = "success"
    error = "error"


class RunStatus(str, Enum):
    running = "running"
    success = "success"
    error = "error"


class ScenarioCreate(BaseModel):
    product_type: ProductType = ProductType.avia
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


class PlatformOut(BaseModel):
    id: int
    code: str
    display_name: str
    base_url: str
    sort_order: int


class ResultOut(BaseModel):
    platform: PlatformOut
    price_rub: float | None = None
    offer_url: str | None = None
    error_text: str | None = None


class RunOut(BaseModel):
    id: int
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    results: list[ResultOut] = []


class ScenarioOut(BaseModel):
    id: int
    title: str
    product_type: ProductType
    origin_label: str
    origin_code: str
    destination_label: str
    destination_code: str
    date_departure: date
    date_return: date | None
    time_departure_pref: str | None
    time_return_pref: str | None
    passengers_adults: int
    cabin_class: str
    direct_only: bool
    baggage_included: bool
    tariff_notes: str | None
    status: ScenarioStatus
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    latest_run: RunOut | None = None


class ScenarioListItem(BaseModel):
    id: int
    title: str
    product_type: ProductType
    status: ScenarioStatus
    created_at: datetime
    updated_at: datetime
    latest_run_status: RunStatus | None = None
    latest_run_finished_at: datetime | None = None


class HealthOut(BaseModel):
    ok: bool
    db: bool
    detail: str | None = None


class MessageOut(BaseModel):
    message: str
    scenario_id: int | None = None
    run_id: int | None = None


class RawJSON(BaseModel):
    data: dict[str, Any]


class ScheduleCreate(BaseModel):
    scenario_id: int
    interval_minutes: int = Field(default=1440, ge=5, le=10080)
    enabled: bool = True


class ScheduleOut(BaseModel):
    id: int
    scenario_id: int
    scenario_title: str
    interval_minutes: int
    enabled: bool
    last_scheduled_run_at: datetime | None
    created_at: datetime


class SchedulePatch(BaseModel):
    interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    enabled: bool | None = None


class AnalyticsSummaryOut(BaseModel):
    scenarios_total: int
    runs_total: int
    runs_last_24h: int
    runs_success_last_24h: int
    runs_error_last_24h: int
    scenarios_by_status: dict[str, int]
    parser_mode: str


class PublicStatusOut(BaseModel):
    service: str
    db: bool
    ok: bool
    detail: str | None = None
