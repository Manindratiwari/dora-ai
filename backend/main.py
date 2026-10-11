"""Dora backend: FastAPI with a configurable LLM provider. Secrets come from .env only."""
import os
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()
PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
API_KEY = os.getenv("LLM_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))

SYSTEM = (
    "You are Dora, a warm, caring companion who talks like a real friend, never like a robot or a manual. "
    "Use natural spoken phrasing: contractions, short sentences, and a light touch of fillers such as acha, hmm or arre "
    "when it fits the user's language. Match their mood. Reply in the same language and script the user used "
    "(Devanagari Hindi, Roman Hinglish, or English). Keep it to 1-3 short sentences because it is spoken aloud; "
    "no markdown, lists or emojis. You cannot set reminders, browse the web, check live weather or take actions "
    "on devices; if asked, say so honestly and offer what you can do (chat, explain, draft text)."
)

app = FastAPI(title="Dora")
hits: dict[str, deque] = defaultdict(deque)


class Msg(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatIn(BaseModel):
    messages: list[Msg] = Field(min_length=1, max_length=20)


def check_rate(ip: str) -> None:
    now, q = time.time(), hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Too many requests")
    q.append(now)


async def call_llm(messages: list[dict]) -> str:
    if not API_KEY:
        raise HTTPException(503, "LLM_API_KEY is not set in backend/.env")
    system = SYSTEM + " Current local date and time: " + datetime.now().strftime("%A, %d %B %Y, %I:%M %p") + "."
    async with httpx.AsyncClient(timeout=40) as c:
        if PROVIDER == "anthropic":
            r = await c.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": MODEL, "max_tokens": 400, "system": system, "messages": messages},
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        if PROVIDER == "openai":
            r = await c.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": MODEL, "max_tokens": 400, "messages": [{"role": "system", "content": system}] + messages},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    raise HTTPException(500, "Unknown LLM_PROVIDER")


@app.post("/api/chat")
async def chat(body: ChatIn, request: Request):
    check_rate(request.client.host if request.client else "unknown")
    if body.messages[-1].role != "user" or body.messages[0].role != "user":
        raise HTTPException(422, "Conversation must start and end with a user message")
    try:
        reply = await call_llm([m.model_dump() for m in body.messages])
    except httpx.HTTPError:
        raise HTTPException(502, "The LLM provider returned an error")
    return {"reply": reply.strip()}


@app.get("/api/health")
def health():
    return {"ok": True, "provider": PROVIDER, "key_set": bool(API_KEY)}


# Serve the frontend from the same origin so the browser treats it as a normal secure page (mic works).
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static", html=True), name="static")
