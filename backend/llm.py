"""LLM 调用：支持 OpenAI 兼容接口 + Anthropic（Right Code Claude）。"""

from __future__ import annotations

import os

import httpx
from openai import OpenAI


def _provider_for_model(model: str) -> str:
    explicit = os.environ.get("API_PROVIDER", "").strip().lower()
    if explicit in ("anthropic", "openai"):
        return explicit
    if model.lower().startswith("claude"):
        return "anthropic"
    return "openai"


def _chat_openai(api_key: str, model: str, system: str, user: str, max_tokens: int) -> str:
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.85,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


def _chat_anthropic(api_key: str, model: str, system: str, user: str, max_tokens: int) -> str:
    base_url = os.environ.get(
        "ANTHROPIC_BASE_URL", "https://www.right.codes/claude"
    ).rstrip("/")
    resp = httpx.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": 0.85,
        },
        timeout=120.0,
    )
    if resp.status_code >= 400:
        detail = resp.text[:500]
        raise RuntimeError(f"Claude API 错误 {resp.status_code}: {detail}")
    data = resp.json()
    return "".join(
        part.get("text", "")
        for part in data.get("content", [])
        if part.get("type") == "text"
    ).strip()


def chat(api_key: str, model: str, system: str, user: str, max_tokens: int = 512) -> str:
    provider = _provider_for_model(model)
    if provider == "anthropic":
        return _chat_anthropic(api_key, model, system, user, max_tokens)
    return _chat_openai(api_key, model, system, user, max_tokens)
