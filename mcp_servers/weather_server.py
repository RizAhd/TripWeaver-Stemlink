import os
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from mcp_servers import open_meteo_client

mcp = FastMCP(
    "tripweaver-weather",
    host=os.getenv("WEATHER_MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("WEATHER_MCP_PORT", "8003")),
    stateless_http=True,
)


@mcp.tool()
def get_forecast(city: str, days: int = 5) -> Dict[str, Any]:
    """Get the daily weather outlook for a city.

    Use this when the traveller asks what the weather will be like, whether to
    pack for rain, or how warm somewhere will be while they are there.

    Args:
        city: City to look up, for example Tokyo, Bangkok or Colombo.
        days: How many days ahead to report, from 1 to 16. Defaults to 5.

    Returns:
        On success, ok is true, place names the city that was matched, and
        outlook holds one entry per day with a high, a low and a rain chance.
        On failure, ok is false and error explains what went wrong.
    """
    return open_meteo_client.forecast(city, days)


@mcp.tool()
def find_place(city: str) -> Dict[str, Any]:
    """Check which place a city name resolves to before asking for a forecast.

    Use this when a city name is ambiguous and you want to confirm the country
    before reporting weather for the wrong place.

    Args:
        city: City name to resolve.

    Returns:
        On success, ok is true and place holds the matched name, country and
        timezone. On failure, ok is false and error explains what went wrong.
    """
    return open_meteo_client.locate(city)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
