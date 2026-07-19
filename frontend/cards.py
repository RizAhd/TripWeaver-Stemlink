from html import escape
from typing import List

CARD_CSS = """
.tw-cards {display: flex; flex-direction: column; gap: 10px; margin: 2px 0 6px 0;}
.tw-cards-title {
  font-family: 'Fraunces', Georgia, serif; font-size: 0.82rem; font-weight: 600;
  letter-spacing: 0.06em; text-transform: uppercase; color: #5b6b7a; margin: 14px 0 2px 0;
}
.tw-card {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 14px;
  border: 1px solid #e2ded4; border-radius: 13px; background: #ffffff; padding: 13px 15px;
}
.tw-card-main {min-width: 0;}
.tw-card-name {
  font-weight: 600; color: #12212e; font-size: 0.95rem;
  margin-bottom: 3px; overflow-wrap: anywhere;
}
.tw-card-meta {color: #5b6b7a; font-size: 0.83rem; line-height: 1.5;}
.tw-card-side {text-align: right; white-space: nowrap;}
.tw-card-price {font-weight: 600; color: #12212e; font-size: 0.95rem;}
.tw-card-unit {color: #5b6b7a; font-size: 0.76rem;}
.tw-pill {
  display: inline-block; margin-top: 6px; padding: 2px 9px; border-radius: 999px;
  font-size: 0.73rem; font-weight: 600; letter-spacing: 0.02em;
}
.tw-pill-open {background: #e7f2f0; color: #0a5f68;}
.tw-pill-none {background: #f2e9e4; color: #96543f;}
.tw-pill-booked {background: #0e7c86; color: #f6f3ec;}
.tw-more {color: #5b6b7a; font-size: 0.8rem; padding-left: 2px;}

@media (min-width: 720px) {
  .tw-cards {display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px;}
}

@media (max-width: 640px) {
  .tw-card {flex-direction: column; gap: 6px;}
  .tw-card-side {text-align: left;}
}

@media (max-width: 420px) {
  .tw-card {padding: 11px 12px;}
  .tw-cards-title {margin-top: 12px;}
}
"""

LIMIT = 6


def _text(value, fallback="") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value))


def _airport(value) -> str:
    if isinstance(value, dict):
        return _text(value.get("airport") or value.get("city"), "?")
    return _text(value, "?")


def _availability(count, noun: str) -> str:
    try:
        left = int(count)
    except (TypeError, ValueError):
        return ""
    if left <= 0:
        return '<span class="tw-pill tw-pill-none">Sold out</span>'
    return '<span class="tw-pill tw-pill-open">%d %s left</span>' % (left, noun)


def _hotel_card(hotel: dict) -> str:
    stars = hotel.get("starRating")
    stars_text = ("%s star" % stars) if stars else ""
    meta = " . ".join(part for part in [_text(hotel.get("city")), stars_text] if part)
    return (
        '<div class="tw-card">'
        '<div class="tw-card-main">'
        '<div class="tw-card-name">%s</div>'
        '<div class="tw-card-meta">%s</div>'
        "%s"
        "</div>"
        '<div class="tw-card-side">'
        '<div class="tw-card-price">%s %s</div>'
        '<div class="tw-card-unit">per night</div>'
        "</div>"
        "</div>"
    ) % (
        _text(hotel.get("name"), "Hotel"),
        meta,
        _availability(hotel.get("availableRooms"), "rooms"),
        _text(hotel.get("currency")),
        _text(hotel.get("pricePerNight"), "?"),
    )


def _flight_card(flight: dict) -> str:
    route = "%s to %s" % (_airport(flight.get("origin")), _airport(flight.get("destination")))
    times = " - ".join(
        part for part in [_text(flight.get("departureTime")), _text(flight.get("arrivalTime"))] if part
    )
    meta = " . ".join(part for part in [route, _text(flight.get("flightDate")), times] if part)
    return (
        '<div class="tw-card">'
        '<div class="tw-card-main">'
        '<div class="tw-card-name">%s %s</div>'
        '<div class="tw-card-meta">%s</div>'
        "%s"
        "</div>"
        '<div class="tw-card-side">'
        '<div class="tw-card-price">%s %s</div>'
        '<div class="tw-card-unit">per seat</div>'
        "</div>"
        "</div>"
    ) % (
        _text(flight.get("airline"), "Flight"),
        _text(flight.get("flightNumber")),
        meta,
        _availability(flight.get("availableSeats"), "seats"),
        _text(flight.get("currency")),
        _text(flight.get("price"), "?"),
    )


def _booking_card(booking: dict) -> str:
    bits = []
    if booking.get("numberOfNights"):
        bits.append("%s nights" % _text(booking["numberOfNights"]))
    if booking.get("seatNumber"):
        bits.append("seat %s" % _text(booking["seatNumber"]))
    if booking.get("totalPrice"):
        bits.append("total %s" % _text(booking["totalPrice"]))
    return (
        '<div class="tw-card">'
        '<div class="tw-card-main">'
        '<div class="tw-card-name">%s</div>'
        '<div class="tw-card-meta">%s</div>'
        '<span class="tw-pill tw-pill-booked">%s</span>'
        "</div>"
        "</div>"
    ) % (
        _text(booking.get("bookingReference"), "Booking"),
        " . ".join(bits),
        _text(booking.get("status"), "confirmed").capitalize(),
    )


def _section(title: str, records: List[dict], builder) -> str:
    if not records:
        return ""
    shown = [builder(record) for record in records[:LIMIT]]
    extra = len(records) - LIMIT
    more = '<div class="tw-more">and %d more</div>' % extra if extra > 0 else ""
    return '<div class="tw-cards-title">%s</div><div class="tw-cards">%s</div>%s' % (
        escape(title),
        "".join(shown),
        more,
    )


def render(results: dict) -> str:
    results = results or {}
    parts = [
        _section("Bookings", results.get("bookings") or [], _booking_card),
        _section("Hotels", results.get("hotel_results") or [], _hotel_card),
        _section("Flights", results.get("flight_results") or [], _flight_card),
    ]
    return "".join(part for part in parts if part)
