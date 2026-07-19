from typing import List, Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from .entity import GraphState
from .llm import llm
from .prompts import (
    AMBIGUOUS_PROMPT,
    GENERAL_QA_PROMPT,
    ROUTER_PROMPT,
    agent_prompt,
)


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


def make_agent(tools: List[BaseTool], prompt_template: str, activity_label: str):
    model = llm.bind_tools(tools)

    async def agent(state: GraphState) -> dict:
        writer = get_stream_writer()
        writer({"type": "activity", "state": "RESPONDING", "label": activity_label})

        messages = [SystemMessage(content=agent_prompt(prompt_template))] + list(state["messages"])
        response = await model.ainvoke(messages)
        return {"messages": [response]}

    return agent


def make_plain_agent(prompt_template: str, activity_label: str):
    async def plain(state: GraphState) -> dict:
        writer = get_stream_writer()
        writer({"type": "activity", "state": "RESPONDING", "label": activity_label})

        messages = [SystemMessage(content=agent_prompt(prompt_template))] + list(state["messages"])
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    return plain


def make_unavailable_agent(message: str):
    async def unavailable(state: GraphState) -> dict:
        return {"messages": [AIMessage(content=message)]}

    return unavailable


general_qa = make_plain_agent(GENERAL_QA_PROMPT, "Answering your question...")
ambiguous_agent = make_plain_agent(AMBIGUOUS_PROMPT, "Checking what you need...")
