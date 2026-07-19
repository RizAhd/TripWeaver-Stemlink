import os
from typing import Any, Dict, List, Optional

import httpx

TIMEOUT = httpx.Timeout(10.0, connect=5.0)

GEOCODE_URL = os.getenv("GEOCODE_BASE_URL", "https://geocoding-api.open-meteo.com/v1/search")
FORECAST_URL = os.getenv("FORECAST_BASE_URL", "https://api.open-meteo.com/v1/forecast")

DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,precipitation_probability_max"

MAX_DAYS = 16


def _failure(message: str) -> Dict[str, Any]:
    return {"ok": False, "error": message}


def _describe(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "The weather service did not respond in time."
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code >= 500:
            return "The weather service is temporarily unavailable."
        return "The weather service rejected the request."
    return "The weather service could not be reached."


def _get(url: str, params: dict) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
    except Exception as exc:
        return _failure(_describe(exc))


def locate(city: str) -> Dict[str, Any]:
    result = _get(GEOCODE_URL, {"name": city, "count": 1, "format": "json"})
    if not result["ok"]:
        return result

    matches = result["data"].get("results") or []
    if not matches:
        return _failure("I could not find a place called %s." % city)

    place = matches[0]
    return {
        "ok": True,
        "place": {
            "name": place.get("name"),
            "country": place.get("country"),
            "latitude": place.get("latitude"),
            "longitude": place.get("longitude"),
            "timezone": place.get("timezone"),
        },
    }


def forecast(city: str, days: int = 5) -> Dict[str, Any]:
    found = locate(city)
    if not found["ok"]:
        return found

    place = found["place"]
    span = max(1, min(int(days or 5), MAX_DAYS))

    result = _get(
        FORECAST_URL,
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "daily": DAILY_FIELDS,
            "forecast_days": span,
            "timezone": "auto",
        },
    )
    if not result["ok"]:
        return result

    daily = result["data"].get("daily") or {}
    units = result["data"].get("daily_units") or {}
    dates: List[str] = daily.get("time") or []

    outlook = []
    for index, day in enumerate(dates):
        outlook.append(
            {
                "date": day,
                "high": _at(daily.get("temperature_2m_max"), index),
                "low": _at(daily.get("temperature_2m_min"), index),
                "rain_chance": _at(daily.get("precipitation_probability_max"), index),
            }
        )

    return {
        "ok": True,
        "place": place,
        "temperature_unit": units.get("temperature_2m_max", "C"),
        "rain_chance_unit": units.get("precipitation_probability_max", "%"),
        "outlook": outlook,
    }


def _at(values: Optional[list], index: int):
    if not values or index >= len(values):
        return None
    return values[index]
