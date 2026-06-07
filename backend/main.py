"""TopTalk领晤 Web API"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from collections import defaultdict

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import create_token, get_current_user, hash_password, security, verify_password
from database import (
    admin_create_code,
    admin_create_codes_batch,
    create_user,
    deduct_credit,
    generate_codes,
    get_user_by_username,
    init_db,
    normalize_code,
    redeem_code,
    seed_codes_from_env,
)
from orchestrator import load_masters, run_roundtable

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="TopTalk领晤", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_HOUR", "20"))
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _auth_required() -> bool:
    return os.environ.get("AUTH_REQUIRED", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )


@app.on_event("startup")
def startup():
    init_db()
    seed_codes_from_env()


def _check_rate_limit(ip: str) -> None:
    if RATE_LIMIT <= 0:
        return
    now = time.time()
    _rate_buckets[ip] = [t for t in _rate_buckets[ip] if now - t < 3600]
    if len(_rate_buckets[ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail=f"请求过于频繁（每小时限 {RATE_LIMIT} 次）")
    _rate_buckets[ip].append(now)


def _check_admin_secret(secret: str) -> None:
    expected = os.environ.get("ADMIN_SECRET", "").strip()
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="管理员密钥错误")


def _verify_faka_signature(code: str, credits: int, order_id: str | None, signature: str | None) -> None:
    webhook_secret = os.environ.get("FAKA_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        return
    if not signature:
        raise HTTPException(status_code=403, detail="缺少签名")
    payload = f"{code}|{credits}|{order_id or ''}"
    expected = hmac.new(
        webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="签名校验失败")


def _server_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="服务未配置 OPENAI_API_KEY，请联系管理员。",
        )
    return key


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_\u4e00-\u9fff]+$")
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=128)


class DiscussRequest(BaseModel):
    question: str = Field(..., min_length=4, max_length=2000)
    participants: list[str] = Field(..., min_length=2, max_length=4)


class AdminCodeRequest(BaseModel):
    admin_secret: str
    code: str = Field(..., min_length=4, max_length=128)
    credits: int = Field(..., ge=1, le=1000)
    max_uses: int = Field(default=1, ge=1, le=100000)


class AdminBatchCodesRequest(BaseModel):
    admin_secret: str
    codes: list[str] = Field(..., min_length=1, max_length=500)
    credits: int = Field(..., ge=1, le=1000)
    max_uses: int = Field(default=1, ge=1, le=100000)


class AdminGenerateCodesRequest(BaseModel):
    admin_secret: str
    count: int = Field(..., ge=1, le=500)
    credits: int = Field(..., ge=1, le=1000)
    prefix: str = Field(default="TT", min_length=2, max_length=16)


class FakaWebhookRequest(BaseModel):
    """发卡平台回调：支付成功后把卡密登记到 TopTalk。"""
    webhook_secret: str
    code: str = Field(..., min_length=4, max_length=128)
    credits: int = Field(..., ge=1, le=1000)
    order_id: str | None = Field(default=None, max_length=128)
    signature: str | None = Field(default=None, max_length=128)


@app.get("/api/config")
def get_config():
    model = os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")
    provider = os.environ.get("API_PROVIDER", "").strip().lower()
    if not provider:
        provider = "anthropic" if model.lower().startswith("claude") else "openai"
    return {
        "appName": "TopTalk领晤",
        "serverProvidesKey": bool(os.environ.get("OPENAI_API_KEY", "").strip()),
        "needsUserKey": False,
        "defaultModel": model,
        "apiProvider": provider,
        "rateLimitPerHour": RATE_LIMIT if RATE_LIMIT > 0 else None,
        "authRequired": _auth_required(),
    }


@app.get("/api/masters")
def get_masters():
    return load_masters()


@app.post("/api/auth/register")
def register(req: RegisterRequest):
    if get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    user_id = create_user(req.username, hash_password(req.password))
    token = create_token(user_id, req.username)
    return {
        "token": token,
        "user": {"username": req.username, "credits": 0},
        "message": "注册成功，请兑换口令获取领晤次数",
    }


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user["id"], user["username"])
    return {
        "token": token,
        "user": {"username": user["username"], "credits": user["credits"]},
    }


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


@app.post("/api/auth/redeem")
def redeem(req: RedeemRequest, user: dict = Depends(get_current_user)):
    credits, message = redeem_code(user["id"], req.code)
    if credits == 0:
        raise HTTPException(status_code=400, detail=message)
    updated = get_user_by_username(user["username"])
    return {
        "message": message,
        "creditsAdded": credits,
        "credits": updated["credits"] if updated else user["credits"] + credits,
    }


@app.post("/api/admin/codes")
def admin_codes(req: AdminCodeRequest):
    _check_admin_secret(req.admin_secret)
    admin_create_code(req.code, req.credits, req.max_uses)
    return {"ok": True, "code": normalize_code(req.code), "credits": req.credits}


@app.post("/api/admin/codes/batch")
def admin_codes_batch(req: AdminBatchCodesRequest):
    """批量导入发卡网已有的卡密（一行一个）。"""
    _check_admin_secret(req.admin_secret)
    result = admin_create_codes_batch(req.codes, req.credits, req.max_uses)
    return {"ok": True, **result}


@app.post("/api/admin/codes/generate")
def admin_codes_generate(req: AdminGenerateCodesRequest):
    """由 TopTalk 批量生成卡密，导出后上传到发卡网库存。"""
    _check_admin_secret(req.admin_secret)
    codes = generate_codes(req.count, req.credits, req.prefix)
    return {"ok": True, "count": len(codes), "credits": req.credits, "codes": codes}


@app.post("/api/webhooks/faka")
def faka_webhook(req: FakaWebhookRequest):
    """
    发卡平台「API 对接发货」回调。
    买家付款后，发卡网 POST 此接口，把卡密登记进 TopTalk，用户再到网站兑换。
    """
    webhook_secret = os.environ.get("FAKA_WEBHOOK_SECRET", "").strip()
    if not webhook_secret or req.webhook_secret != webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook 密钥错误")

    code = normalize_code(req.code)
    _verify_faka_signature(code, req.credits, req.order_id, req.signature)
    is_new = admin_create_code(code, req.credits, max_uses=1)
    return {
        "ok": True,
        "code": code,
        "credits": req.credits,
        "status": "created" if is_new else "updated",
        "message": "卡密已登记，用户可在 TopTalk 兑换",
    }


async def _resolve_discuss_user(
    creds=Depends(security),
) -> dict:
    if not _auth_required():
        return {"id": 0, "username": "guest", "credits": 999}
    return await get_current_user(creds)


@app.post("/api/discuss")
async def discuss(
    req: DiscussRequest,
    request: Request,
    user: dict = Depends(_resolve_discuss_user),
):
    if _auth_required():
        if user["credits"] < 1:
            raise HTTPException(
                status_code=402,
                detail="领晤次数不足，请先兑换口令",
            )

    _check_rate_limit(request.client.host if request.client else "unknown")

    valid_ids = {m["id"] for m in load_masters()}
    for pid in req.participants:
        if pid not in valid_ids:
            raise HTTPException(status_code=400, detail=f"未知参与者: {pid}")

    if _auth_required() and not deduct_credit(user["id"]):
        raise HTTPException(status_code=402, detail="领晤次数不足")

    model = os.environ.get("DEFAULT_MODEL", "gpt-4o-mini")
    try:
        result = run_roundtable(
            question=req.question.strip(),
            participant_ids=req.participants,
            api_key=_server_api_key(),
            model=model,
        )
        if _auth_required():
            result["creditsRemaining"] = user["credits"] - 1
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
