from typing import Annotated, List, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]

    intent: str

    hotel_results: List[dict]
    flight_results: List[dict]
    bookings: List[dict]
