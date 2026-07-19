from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from entity import ChatRequest, ChatResponse
from agents.graph import build_graph
from agents.mcp_client import load_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    hotel_tools, flight_tools = await load_tools()
    app.state.graph = build_graph(hotel_tools, flight_tools)
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
async def hello():
    return {"message": "Hello, World!"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await app.state.graph.ainvoke(build_state(request))

    return ChatResponse(
        response=message_text(result["messages"][-1]),
        hotel_results=result.get("hotel_results", []),
        flight_results=result.get("flight_results", []),
        bookings=result.get("bookings", []),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
