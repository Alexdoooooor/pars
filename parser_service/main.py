from __future__ import annotations

import logging
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from parser_service.config import ParserServiceSettings, get_parser_settings
from parser_service.engine import run_parse
from parser_service.platforms_data import PLATFORMS
from parser_service.schemas import HealthOut, ParseResponse, ScenarioPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Price Parser Service",
    description="HTTP API сбора цен по площадкам. Защита: заголовок X-Parser-Api-Key.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_parser_key(
    x_parser_api_key: str | None = Header(None, alias="X-Parser-Api-Key"),
    settings: ParserServiceSettings = Depends(get_parser_settings),
) -> None:
    if not settings.parser_service_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="На сервисе не задан PARSER_SERVICE_API_KEY",
        )
    if not x_parser_api_key or not secrets.compare_digest(
        x_parser_api_key, settings.parser_service_api_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствует X-Parser-Api-Key",
        )


@app.get("/health", response_model=HealthOut)
def health(settings: ParserServiceSettings = Depends(get_parser_settings)) -> HealthOut:
    return HealthOut(
        service="price-parser",
        ok=True,
        parser_mode=settings.parser_mode,
        api_key_configured=bool(settings.parser_service_api_key),
    )


@app.get("/v1/platforms")
def list_platforms(_: None = Depends(require_parser_key)) -> list[dict]:
    return list(PLATFORMS)


@app.post("/v1/parse", response_model=ParseResponse)
def parse_scenario(
    body: ScenarioPayload,
    settings: ParserServiceSettings = Depends(get_parser_settings),
    _: None = Depends(require_parser_key),
) -> ParseResponse:
    try:
        return run_parse(body, settings.parser_mode)
    except Exception as e:
        logger.exception("parse failed")
        return ParseResponse(ok=False, mode=settings.parser_mode, results=[], detail=str(e))
