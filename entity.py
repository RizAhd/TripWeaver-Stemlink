from pydantic import BaseModel
from typing import List, Literal


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatTurn] = []
    hotel_results: List[dict] = []
    flight_results: List[dict] = []
    bookings: List[dict] = []


class ChatResponse(BaseModel):
    response: str
    hotel_results: List[dict] = []
    flight_results: List[dict] = []
    bookings: List[dict] = []
