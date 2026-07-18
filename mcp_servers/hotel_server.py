import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from mcp_servers import convex_client

mcp = FastMCP(
    "tripweaver-hotels",
    host=os.getenv("HOTEL_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("HOTEL_MCP_PORT", "8001")),
    stateless_http=True,
)


@mcp.tool()
def list_hotels() -> Dict[str, Any]:
    """List every hotel the travel service currently offers.

    Use this when the traveller asks to see all hotels without naming a city.

    Returns:
        On success, ok is true and hotels holds the matching records. On
        failure, ok is false and error explains what went wrong.
    """
    return convex_client.list_hotels()


@mcp.tool()
def search_hotels(
    city: str,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
) -> Dict[str, Any]:
    """Search hotels in one city, optionally narrowed by stay dates.

    Args:
        city: City to search, for example Bangkok, Tokyo or Colombo.
        check_in: Optional check-in date as YYYY-MM-DD.
        check_out: Optional check-out date as YYYY-MM-DD.

    Returns:
        On success, ok is true and hotels holds the matching records, which may
        be an empty list when the city has no availability. On failure, ok is
        false and error explains what went wrong.
    """
    return convex_client.search_hotels(city, check_in, check_out)


@mcp.tool()
def book_hotel(
    hotel_id: str,
    guest_name: str,
    guest_email: str,
    check_in_date: str,
    check_out_date: str,
    room_type: str,
) -> Dict[str, Any]:
    """Reserve a room at one hotel.

    Every argument is required. Ask the traveller for anything you are missing
    rather than guessing a value.

    Args:
        hotel_id: The id field of a hotel returned by list_hotels or search_hotels.
        guest_name: Full name of the guest.
        guest_email: Email address of the guest.
        check_in_date: Check-in date as YYYY-MM-DD.
        check_out_date: Check-out date as YYYY-MM-DD.
        room_type: Room type such as single, double or suite.

    Returns:
        On success, ok is true and booking holds the reference, status and
        total price the service returned. On failure, ok is false and error
        explains what went wrong.
    """
    return convex_client.book_hotel(
        hotel_id,
        guest_name,
        guest_email,
        check_in_date,
        check_out_date,
        room_type,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
