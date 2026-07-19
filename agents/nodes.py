import json
from typing import List, Literal, Optional

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from .entity import GraphState
from .llm import llm
from .prompts import (
    AMBIGUOUS_PROMPT,
    GENERAL_QA_PROMPT,
    ROUTER_PROMPT,
    agent_prompt,
)

BOOKING_TOOLS = ("book_hotel", "book_flight")


class IntentDecision(BaseModel):
    intent: Literal["hotel", "flight", "general", "ambiguous"] = Field(
        default="general",
        description="Which specialist should answer the traveller.",
    )


intent_classifier = llm.with_structured_output(IntentDecision)


def tool_error_message(exc: Exception) -> str:
    return (
        "That travel service could not be reached. Tell the traveller the service "
        "is unavailable right now and suggest trying again shortly."
    )


def tool_payload(message: AnyMessage) -> Optional[dict]:
    artifact = getattr(message, "artifact", None)
    if isinstance(artifact, dict):
        result = artifact.get("structured_content", {}).get("result")
        if isinstance(result, dict):
            return result

    content = message.content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                content = block.get("text", "")
                break

    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None

    return None


def tool_succeeded(message: AnyMessage) -> bool:
    if getattr(message, "status", None) == "error":
        return False

    payload = tool_payload(message)
    if isinstance(payload, dict) and payload.get("ok") is False:
        return False

    return True


def collect_results(state: GraphState, messages: List[AnyMessage]) -> dict:
    collected = {}
    bookings = list(state.get("bookings", []))

    for message in messages:
        payload = tool_payload(message)
        if not isinstance(payload, dict) or not payload.get("ok"):
            continue

        if isinstance(payload.get("hotels"), list):
            collected["hotel_results"] = payload["hotels"]
        if isinstance(payload.get("flights"), list):
            collected["flight_results"] = payload["flights"]
        if isinstance(payload.get("booking"), dict):
            bookings.append(payload["booking"])

    if len(bookings) != len(state.get("bookings", [])):
        collected["bookings"] = bookings

    return collected


def _hotel_line(index: int, hotel: dict) -> str:
    return "%d. %s in %s, %s star, %s %s per night, %s rooms left, id %s" % (
        index,
        hotel.get("name", "unknown hotel"),
        hotel.get("city", "unknown city"),
        hotel.get("starRating", "?"),
        hotel.get("currency", ""),
        hotel.get("pricePerNight", "?"),
        hotel.get("availableRooms", "?"),
        hotel.get("id", ""),
    )


def _flight_line(index: int, flight: dict) -> str:
    origin = flight.get("origin", {})
    destination = flight.get("destination", {})
    return "%d. %s %s from %s to %s on %s, %s to %s, %s %s, %s seats left, id %s" % (
        index,
        flight.get("airline", "unknown airline"),
        flight.get("flightNumber", ""),
        origin.get("airport", "?") if isinstance(origin, dict) else origin,
        destination.get("airport", "?") if isinstance(destination, dict) else destination,
        flight.get("flightDate", "?"),
        flight.get("departureTime", "?"),
        flight.get("arrivalTime", "?"),
        flight.get("currency", ""),
        flight.get("price", "?"),
        flight.get("availableSeats", "?"),
        flight.get("id", ""),
    )


def _booking_line(booking: dict) -> str:
    parts = ["reference %s" % booking.get("bookingReference", "unknown")]
    if booking.get("status"):
        parts.append("status %s" % booking["status"])
    if booking.get("numberOfNights"):
        parts.append("%s nights" % booking["numberOfNights"])
    if booking.get("seatNumber"):
        parts.append("seat %s" % booking["seatNumber"])
    if booking.get("totalPrice"):
        parts.append("total %s" % booking["totalPrice"])
    return "- " + ", ".join(parts)


def results_context(state: GraphState) -> Optional[SystemMessage]:
    sections = []

    hotels = state.get("hotel_results") or []
    if hotels:
        lines = [_hotel_line(i, h) for i, h in enumerate(hotels[:10], start=1)]
        sections.append("Hotels already shown to the traveller, in this order:\n" + "\n".join(lines))

    flights = state.get("flight_results") or []
    if flights:
        lines = [_flight_line(i, f) for i, f in enumerate(flights[:10], start=1)]
        sections.append("Flights already shown to the traveller, in this order:\n" + "\n".join(lines))

    bookings = state.get("bookings") or []
    if bookings:
        lines = [_booking_line(b) for b in bookings]
        sections.append("Bookings confirmed so far in this conversation:\n" + "\n".join(lines))

    if not sections:
        return None

    return SystemMessage(
        content=(
            "\n\n".join(sections)
            + "\n\nWhen the traveller refers to an option by its position, such as the "
            "second hotel, take the id from this list rather than searching again."
        )
    )


async def router(state: GraphState) -> dict:
    writer = get_stream_writer()
    writer({"type": "activity", "state": "ROUTING", "label": "Understanding your request..."})

    messages = [SystemMessage(content=ROUTER_PROMPT)] + list(state["messages"])

    try:
        decision = await intent_classifier.ainvoke(messages)
        intent = decision.intent
    except Exception:
        intent = "general"

    return {"intent": intent}


def route_by_intent(state: GraphState) -> str:
    return state.get("intent", "general")


def _announce(state: GraphState, response: AIMessage, writer) -> None:
    if getattr(response, "tool_calls", None):
        return

    answered_from_tools = any(
        message.__class__.__name__ == "ToolMessage" for message in state["messages"]
    )
    if answered_from_tools:
        return

    writer({"type": "activity", "state": "CLARIFYING", "label": "Asking for a missing detail..."})


def make_agent(tools: List[BaseTool], prompt_template: str, activity_label: str):
    model = llm.bind_tools(tools)

    async def agent(state: GraphState) -> dict:
        writer = get_stream_writer()
        writer({"type": "activity", "state": "RESPONDING", "label": activity_label})

        messages = [SystemMessage(content=agent_prompt(prompt_template))]
        context = results_context(state)
        if context is not None:
            messages.append(context)
        messages.extend(state["messages"])

        response = await model.ainvoke(messages)
        _announce(state, response, writer)
        return {"messages": [response]}

    return agent


def make_tool_runner(tools: List[BaseTool], searching_label: str, booking_label: str):
    node = ToolNode(tools, handle_tool_errors=tool_error_message)

    async def run_tools(state: GraphState) -> dict:
        writer = get_stream_writer()
        requested = getattr(state["messages"][-1], "tool_calls", None) or []

        for call in requested:
            booking = call["name"] in BOOKING_TOOLS
            writer(
                {
                    "type": "activity",
                    "state": "BOOKING" if booking else "SEARCHING",
                    "label": booking_label if booking else searching_label,
                }
            )
            writer({"type": "tool", "id": call["id"], "name": call["name"], "status": "INVOKED"})

        result = await node.ainvoke(state)
        messages = result["messages"]

        for message in messages:
            writer(
                {
                    "type": "tool",
                    "id": getattr(message, "tool_call_id", ""),
                    "name": getattr(message, "name", ""),
                    "status": "SUCCEEDED" if tool_succeeded(message) else "FAILED",
                }
            )

        return {"messages": messages, **collect_results(state, messages)}

    return run_tools


def make_plain_agent(prompt_template: str, activity_label: str, activity_state: str = "RESPONDING"):
    async def plain(state: GraphState) -> dict:
        writer = get_stream_writer()
        writer({"type": "activity", "state": activity_state, "label": activity_label})

        messages = [SystemMessage(content=agent_prompt(prompt_template))] + list(state["messages"])
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    return plain


def make_unavailable_agent(message: str):
    async def unavailable(state: GraphState) -> dict:
        return {"messages": [AIMessage(content=message)]}

    return unavailable


general_qa = make_plain_agent(GENERAL_QA_PROMPT, "Answering your question...")
ambiguous_agent = make_plain_agent(AMBIGUOUS_PROMPT, "Checking what you need...", "CLARIFYING")
