"""Справочник площадок (синхронизирован с pi_platform в основной БД)."""

from __future__ import annotations

from typing import TypedDict


class PlatformDef(TypedDict):
    code: str
    display_name: str
    base_url: str
    sort_order: int


PLATFORMS: list[PlatformDef] = [
    {"code": "vtb", "display_name": "ВТБ Путешествия", "base_url": "https://vtb.aviakassa.ru/", "sort_order": 10},
    {"code": "tbank", "display_name": "Т-Путешествия", "base_url": "https://www.tbank.ru/travel/", "sort_order": 20},
    {"code": "alfa", "display_name": "Альфа Тревел", "base_url": "https://alfabank.ru/travel/", "sort_order": 30},
    {"code": "aviasales", "display_name": "Aviasales", "base_url": "https://www.aviasales.ru/", "sort_order": 40},
    {"code": "ostrovok", "display_name": "Островок", "base_url": "https://ostrovok.ru/", "sort_order": 50},
    {"code": "yandex", "display_name": "Яндекс Путешествия", "base_url": "https://travel.yandex.ru/", "sort_order": 60},
    {"code": "ozon", "display_name": "Ozon Travel", "base_url": "https://www.ozon.ru/travel", "sort_order": 70},
    {"code": "tutu", "display_name": "tutu.ru", "base_url": "https://www.tutu.ru/", "sort_order": 80},
]
