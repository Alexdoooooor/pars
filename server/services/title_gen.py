from __future__ import annotations

from datetime import date


def build_scenario_title(
    origin_label: str,
    destination_label: str,
    date_departure: date,
    date_return: date | None,
    time_departure_pref: str | None,
    time_return_pref: str | None,
    product_type: str,
) -> str:
    o = origin_label.strip() or "?"
    d = destination_label.strip() or "?"
    leg = f"{o} → {d}"
    dates = date_departure.isoformat()
    if date_return:
        dates = f"{date_departure.isoformat()} / {date_return.isoformat()}"
    times: list[str] = []
    if time_departure_pref:
        times.append(f"туда {time_departure_pref}")
    if time_return_pref:
        times.append(f"обратно {time_return_pref}")
    time_part = f" · {' · '.join(times)}" if times else ""
    type_ru = {"avia": "Авиа", "rail": "Ж/д", "hotel": "Отель"}.get(product_type, product_type)
    return f"{type_ru}: {leg} · {dates}{time_part}"
