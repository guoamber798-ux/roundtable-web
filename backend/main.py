"""思维圆桌 Web API — 支持服务端 API Key，访客无需 nuwa / 无需自备 Key。"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from orchestrator import load_masters, run_roundtable

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="思维圆桌", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 简易限流：每 IP 每小时 N 次（防滥用）
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_HOUR", "10"))
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> None:
    if RATE_LIMIT <= 0:
        return
    now = time.time()
    window = _rate_buckets[ip]
    _rate_buckets[ip] = [t for t in window if now - t < 3600]
    if len(_rate_buckets[ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail=f"请求过于频繁，请稍后再试（每小时限 {RATE_LIMIT} 次）")
    _rate_buckets[ip].append(now)


def _resolve_api_key(client_key: str | None) -> str | None:
    server_key = os.environ.get("OPENAI_API_KEY", "").strip()
    allow_client = os.environ.get("ALLOW_CLIENT_API_KEY", "false").lower() == "true"

    if server_key:
        return server_key
    if allow_client and client_key:
        return client_key.strip()
    if client_key and not server_key:
        return client_key.strip()
    return None


class DiscussRequest(BaseModel):
    question: str = Field(..., min_length=4, max_length=2000)
    participants: list[str] = Field(..., min_length=2, max_length=4)
    api_key: str | None = None
    model: str | None = None


@app.get("/api/config")
def get_config():
    server_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    default_model = os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")
    return {
        "serverProvidesKey": server_key,
        "needsUserKey": not server_key,
        "defaultModel": default_model,
        "rateLimitPerHour": RATE_LIMIT if RATE_LIMIT > 0 else None,
        "bundledPrompts": True,
    }


@app.get("/api/masters")
def get_masters():
    return load_masters()


@app.post("/api/discuss")
def discuss(req: DiscussRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    api_key = _resolve_api_key(req.api_key)
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="服务未配置 AI 能力。站长请在环境变量中设置 OPENAI_API_KEY。",
        )

    model = req.model or os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")

    valid_ids = {m["id"] for m in load_masters()}
    for pid in req.participants:
        if pid not in valid_ids:
            raise HTTPException(status_code=400, detail=f"未知参与者: {pid}")

    try:
        return run_roundtable(
            question=req.question.strip(),
            participant_ids=req.participants,
            api_key=api_key,
            model=model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
