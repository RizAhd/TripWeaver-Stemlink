import logging
import os
from contextlib import asynccontextmanager
from typing import List

import speech
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import EventSourceResponse
from fastapi.sse import ServerSentEvent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from openai import AsyncOpenAI, OpenAIError
from starlette.responses import ClientDisconnect

from entity import ChatRequest, ChatResponse, TranscriptResponse
from agents.graph import build_graph
from agents.mcp_client import load_tools

USER_FACING_NODES = ("hotel_agent", "flight_agent", "weather_agent", "general_qa", "ambiguous")

GRAPH_CONFIG = {"recursion_limit": 12}

UNEXPECTED_ERROR = "Something went wrong while planning your trip. Please try again."

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    hotel_tools, flight_tools, weather_tools = await load_tools()
    logger.info(
        "loaded MCP tools hotel=%d flight=%d weather=%d",
        len(hotel_tools),
        len(flight_tools),
        len(weather_tools),
    )
    app.state.graph = build_graph(hotel_tools, flight_tools, weather_tools)

    try:
        app.state.transcriber = AsyncOpenAI(timeout=45.0, max_retries=1)
    except OpenAIError:
        app.state.transcriber = None
        logger.warning("voice input is off because no OpenAI key was found")

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def message_text(message: AnyMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content

    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def build_messages(request: ChatRequest) -> List[AnyMessage]:
    messages: List[AnyMessage] = []
    for turn in request.history:
        if turn.role == "user":
            messages.append(HumanMessage(content=turn.content))
        else:
            messages.append(AIMessage(content=turn.content))
    messages.append(HumanMessage(content=request.message))
    return messages


def build_state(request: ChatRequest) -> dict:
    return {
        "messages": build_messages(request),
        "intent": "",
        "hotel_results": request.hotel_results,
        "flight_results": request.flight_results,
        "bookings": request.bookings,
    }


@app.get("/")
async def index():
    return {
        "service": "TripWeaver",
        "health": "/health",
        "chat": "/chat/stream",
        "transcribe": "/transcribe",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        result = await app.state.graph.ainvoke(build_state(request), config=GRAPH_CONFIG)
    except Exception:
        return ChatResponse(response=UNEXPECTED_ERROR)

    return ChatResponse(
        response=message_text(result["messages"][-1]),
        hotel_results=result.get("hotel_results", []),
        flight_results=result.get("flight_results", []),
        bookings=result.get("bookings", []),
    )


@app.post("/transcribe", response_model=TranscriptResponse)
async def transcribe(file: UploadFile = File(None)):
    if file is None:
        return TranscriptResponse(**speech.failure("No recording was received. Please try again."))

    try:
        data = await file.read()
    except Exception:
        logger.exception("could not read the uploaded recording")
        return TranscriptResponse(**speech.failure("I could not read that recording. Please try again."))

    result = await speech.transcribe(getattr(app.state, "transcriber", None), data)
    logger.info("transcribe bytes=%d ok=%s", len(data), result["ok"])
    return TranscriptResponse(**result)


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(request: ChatRequest):
    results = {
        "hotel_results": request.hotel_results,
        "flight_results": request.flight_results,
        "bookings": request.bookings,
    }

    try:
        async for mode, chunk in app.state.graph.astream(
            build_state(request),
            stream_mode=["custom", "messages", "updates"],
            config=GRAPH_CONFIG,
        ):
            if mode == "custom":
                yield ServerSentEvent(data=chunk)
                continue

            if mode == "messages":
                message, meta = chunk
                if meta.get("langgraph_node") not in USER_FACING_NODES:
                    continue
                text = message_text(message)
                if text:
                    yield ServerSentEvent(data={"type": "token", "text": text})
                continue

            for delta in chunk.values():
                if not isinstance(delta, dict):
                    continue
                for key in ("hotel_results", "flight_results", "bookings"):
                    if key in delta:
                        results[key] = delta[key]

        yield ServerSentEvent(data={"type": "results", **results})
        yield ServerSentEvent(data={"type": "done"})

    except ClientDisconnect:
        logger.info("client disconnected mid stream")
        return
    except Exception:
        logger.exception("chat stream failed")
        yield ServerSentEvent(
            data={"type": "error", "message": UNEXPECTED_ERROR}
        )
        yield ServerSentEvent(data={"type": "done"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
