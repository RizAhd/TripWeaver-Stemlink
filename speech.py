import os
from typing import Any, Dict

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)

MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")

MAX_AUDIO_BYTES = 20 * 1024 * 1024
MIN_AUDIO_BYTES = 2000
MAX_TRANSCRIPT_CHARS = 2000

HINT = "Travel planning request. May include city names and three letter airport codes."

NOTHING_HEARD = "I did not hear anything. Hold the record button, speak, then stop."
TOO_LONG = "That recording is too long. Please keep it under a minute."
NOT_AVAILABLE = "Voice input is not available on this server right now."
NOT_UNDERSTOOD = "I did not catch that. Please try again."

CONTAINERS = (
    (b"\x1a\x45\xdf\xa3", "webm"),
    (b"OggS", "ogg"),
    (b"RIFF", "wav"),
    (b"fLaC", "flac"),
    (b"ID3", "mp3"),
)


def failure(message: str) -> Dict[str, Any]:
    return {"ok": False, "text": "", "error": message}


def audio_name(data: bytes) -> str:
    for signature, suffix in CONTAINERS:
        if data.startswith(signature):
            return "audio." + suffix

    if len(data) > 12 and data[4:8] == b"ftyp":
        return "audio.mp4"

    return "audio.webm"


def describe(exc: Exception) -> str:
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return NOT_AVAILABLE

    if isinstance(exc, RateLimitError):
        return "Voice input is busy right now. Please try again shortly."

    if isinstance(exc, BadRequestError):
        return "I could not read that recording. Please try again."

    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return "The transcription service did not respond in time. Please try again."

    if isinstance(exc, APIStatusError):
        return "The transcription service is temporarily unavailable."

    return "Something went wrong while listening. Please try again."


async def transcribe(client, data: bytes) -> Dict[str, Any]:
    if client is None:
        return failure(NOT_AVAILABLE)

    if len(data) < MIN_AUDIO_BYTES:
        return failure(NOTHING_HEARD)

    if len(data) > MAX_AUDIO_BYTES:
        return failure(TOO_LONG)

    try:
        result = await client.audio.transcriptions.create(
            model=MODEL,
            file=(audio_name(data), data),
            prompt=HINT,
        )
    except Exception as exc:
        return failure(describe(exc))

    text = (getattr(result, "text", "") or "").strip()
    if not text:
        return failure(NOT_UNDERSTOOD)

    return {"ok": True, "text": text[:MAX_TRANSCRIPT_CHARS], "error": ""}
