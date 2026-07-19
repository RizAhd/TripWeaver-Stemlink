from typing import List

from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .entity import GraphState
from .nodes import (
    ambiguous_agent,
    general_qa,
    make_agent,
    make_unavailable_agent,
    route_by_intent,
    router,
    tool_error_message,
)
from .prompts import (
    FLIGHT_AGENT_PROMPT,
    FLIGHT_UNAVAILABLE,
    HOTEL_AGENT_PROMPT,
    HOTEL_UNAVAILABLE,
)


def _add_domain(
    builder: StateGraph,
    domain: str,
    tools: List[BaseTool],
    prompt_template: str,
    unavailable_message: str,
    activity_label: str,
) -> None:
    agent_node = domain + "_agent"

    if not tools:
        builder.add_node(agent_node, make_unavailable_agent(unavailable_message))
        builder.add_edge(agent_node, END)
        return

    tools_node = domain + "_tools"
    builder.add_node(agent_node, make_agent(tools, prompt_template, activity_label))
    builder.add_node(tools_node, ToolNode(tools, handle_tool_errors=tool_error_message))
    builder.add_conditional_edges(agent_node, tools_condition, {"tools": tools_node, END: END})
    builder.add_edge(tools_node, agent_node)


def build_graph(hotel_tools: List[BaseTool], flight_tools: List[BaseTool]):
    builder = StateGraph(GraphState)

    builder.add_node("router", router)
    builder.add_node("general_qa", general_qa)
    builder.add_node("ambiguous", ambiguous_agent)

    _add_domain(
        builder,
        "hotel",
        hotel_tools,
        HOTEL_AGENT_PROMPT,
        HOTEL_UNAVAILABLE,
        "Searching hotel suggestions...",
    )
    _add_domain(
        builder,
        "flight",
        flight_tools,
        FLIGHT_AGENT_PROMPT,
        FLIGHT_UNAVAILABLE,
        "Searching flight options...",
    )

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "hotel": "hotel_agent",
            "flight": "flight_agent",
            "general": "general_qa",
            "ambiguous": "ambiguous",
        },
    )
    builder.add_edge("general_qa", END)
    builder.add_edge("ambiguous", END)

    return builder.compile()
