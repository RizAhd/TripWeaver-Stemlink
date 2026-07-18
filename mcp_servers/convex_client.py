import os
from typing import Any, Dict, List, Optional

import httpx

TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ConvexConfigError(RuntimeError):
    pass


def base_url() -> str:
    url = os.getenv("CONVEX_BASE_URL")
    if not url:
        raise ConvexConfigError("CONVEX_BASE_URL is not set")
    return url.rstrip("/")


def _failure(message: str) -> Dict[str, Any]:
    return {"ok": False, "error": message}


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""

    if not isinstance(body, dict):
        return ""

    message = body.get("error")
    if not isinstance(message, str) or not message:
        return ""

    if "ArgumentValidationError" in message or "Validator:" in message:
        return "One of the supplied identifiers is not valid."

    if len(message) > 200 or "\n" in message:
        return ""

    return message


def _describe(exc: Exception) -> str:
    if isinstance(exc, ConvexConfigError):
        return "The travel service is not configured."

    if isinstance(exc, httpx.TimeoutException):
        return "The travel service did not respond in time."

    if isinstance(exc, httpx.HTTPStatusError):
        detail = _detail(exc.response)
        if detail:
            return detail
        if exc.response.status_code >= 500:
            return "The travel service is temporarily unavailable."
        return "The travel service rejected the request."

    return "The travel service could not be reached."


def _request(method: str, path: str, params: Optional[dict] = None, payload: Optional[dict] = None) -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(method, base_url() + path, params=params, json=payload)
            response.raise_for_status()
            return {"ok": True, "data": response.json()}
    except Exception as exc:
        return _failure(_describe(exc))


def _identify(item: Any) -> Any:
    if not isinstance(item, dict):
        return item

    record = dict(item)
    if "_id" in record:
        record["id"] = record.pop("_id")
    record.pop("_creationTime", None)
    return record


def _collection(path: str, key: str, params: Optional[dict] = None) -> Dict[str, Any]:
    result = _request("GET", path, params=params)
    if not result["ok"]:
        return result

    body = result["data"]
    items: List[Any] = body.get(key, []) if isinstance(body, dict) else []
    return {"ok": True, key: [_identify(item) for item in items]}


def _confirmation(path: str, payload: dict) -> Dict[str, Any]:
    result = _request("POST", path, payload=payload)
    if not result["ok"]:
        return result

    body = result["data"]
    if isinstance(body, dict) and body.get("success") and isinstance(body.get("booking"), dict):
        return {"ok": True, "booking": body["booking"]}

    return _failure("The travel service did not confirm the booking.")


def _airport(value: str) -> str:
    if len(value) == 3 and value.isalpha():
        return value.upper()
    return value


def list_hotels() -> Dict[str, Any]:
    return _collection("/hotels", "hotels")


def search_hotels(city: str, check_in: Optional[str] = None, check_out: Optional[str] = None) -> Dict[str, Any]:
    params = {"city": city}
    if check_in:
        params["checkIn"] = check_in
    if check_out:
        params["checkOut"] = check_out
    return _collection("/hotels/search", "hotels", params)


def book_hotel(
    hotel_id: str,
    guest_name: str,
    guest_email: str,
    check_in_date: str,
    check_out_date: str,
    room_type: str,
) -> Dict[str, Any]:
    return _confirmation(
        "/hotels/book",
        {
            "hotelId": hotel_id,
            "guestName": guest_name,
            "guestEmail": guest_email,
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "roomType": room_type,
        },
    )


def list_flights() -> Dict[str, Any]:
    return _collection("/flights", "flights")


def search_flights(origin: str, destination: str, date: Optional[str] = None) -> Dict[str, Any]:
    params = {"origin": _airport(origin), "destination": _airport(destination)}
    if date:
        params["date"] = date
    return _collection("/flights/search", "flights", params)


def book_flight(flight_id: str, passenger_name: str, passenger_email: str) -> Dict[str, Any]:
    return _confirmation(
        "/flights/book",
        {
            "flightId": flight_id,
            "passengerName": passenger_name,
            "passengerEmail": passenger_email,
        },
    )
