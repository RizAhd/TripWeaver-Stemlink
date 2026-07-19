import logging
import os
from typing import Dict, List, Tuple

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

HOTEL_SERVER = "hotel"
FLIGHT_SERVER = "flight"
WEATHER_SERVER = "weather"


def connections() -> Dict[str, dict]:
    return {
        HOTEL_SERVER: {
            "transport": "streamable_http",
            "url": os.getenv("HOTEL_MCP_URL", "http://127.0.0.1:8001/mcp"),
        },
        FLIGHT_SERVER: {
            "transport": "streamable_http",
            "url": os.getenv("FLIGHT_MCP_URL", "http://127.0.0.1:8002/mcp"),
        },
        WEATHER_SERVER: {
            "transport": "streamable_http",
            "url": os.getenv("WEATHER_MCP_URL", "http://127.0.0.1:8003/mcp"),
        },
    }


async def _tools_from(client: MultiServerMCPClient, server_name: str) -> List[BaseTool]:
    try:
        return await client.get_tools(server_name=server_name)
    except Exception as exc:
        logger.warning("MCP server %s is unreachable, continuing without it: %s", server_name, exc)
        return []


async def load_tools() -> Tuple[List[BaseTool], List[BaseTool], List[BaseTool]]:
    client = MultiServerMCPClient(connections())
    hotel_tools = await _tools_from(client, HOTEL_SERVER)
    flight_tools = await _tools_from(client, FLIGHT_SERVER)
    weather_tools = await _tools_from(client, WEATHER_SERVER)
    return hotel_tools, flight_tools, weather_tools
