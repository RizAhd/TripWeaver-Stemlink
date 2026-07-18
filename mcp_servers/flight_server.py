import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from mcp_servers import convex_client

mcp = FastMCP(
    "tripweaver-flights",
    host=os.getenv("FLIGHT_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("FLIGHT_MCP_PORT", "8002")),
    stateless_http=True,
)


@mcp.tool()
def list_flights() -> Dict[str, Any]:
    """List every flight the travel service currently offers.

    Use this when the traveller asks to see all flights without naming a route.

    Returns:
        On success, ok is true and flights holds the matching records. On
        failure, ok is false and error explains what went wrong.
    """
    return convex_client.list_flights()


@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Search flights between two places, optionally on one date.

    Args:
        origin: Departure airport code or city, for example NRT or Tokyo.
        destination: Arrival airport code or city, for example ICN or Seoul.
        date: Optional travel date as YYYY-MM-DD.

    Returns:
        On success, ok is true and flights holds the matching records, which may
        be an empty list when nothing serves that route. On failure, ok is false
        and error explains what went wrong.
    """
    return convex_client.search_flights(origin, destination, date)


@mcp.tool()
def book_flight(
    flight_id: str,
    passenger_name: str,
    passenger_email: str,
) -> Dict[str, Any]:
    """Reserve a seat on one flight.

    Every argument is required. Ask the traveller for anything you are missing
    rather than guessing a value.

    Args:
        flight_id: The id field of a flight returned by list_flights or search_flights.
        passenger_name: Full name of the passenger.
        passenger_email: Email address of the passenger.

    Returns:
        On success, ok is true and booking holds the reference, seat and status
        the service returned. On failure, ok is false and error explains what
        went wrong.
    """
    return convex_client.book_flight(flight_id, passenger_name, passenger_email)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
