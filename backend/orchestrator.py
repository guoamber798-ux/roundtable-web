"""圆桌对谈编排：内置人物设定，无需本地 nuwa Skill。"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from openai import OpenAI

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_OUTPUT_CHARS = 3500
PER_SPEAKER_CHARS = 280

_PROMPTS_CACHE: dict[str, str] | None = None


def load_masters() -> list[dict]:
    return json.loads((DATA_DIR / "masters.json").read_text(encoding="utf-8"))


def _load_prompts() -> dict[str, str]:
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is None:
        _PROMPTS_CACHE = json.loads((DATA_DIR / "prompts.json").read_text(encoding="utf-8"))
    return _PROMPTS_CACHE


def get_master_by_id(master_id: str) -> dict | None:
    return next((m for m in load_masters() if m["id"] == master_id), None)


def load_system_prompt(master_id: str) -> str:
    prompts = _load_prompts()
    if master_id in prompts:
        return prompts[master_id]
    master = get_master_by_id(master_id)
    if not master:
        raise ValueError(f"未知大师: {master_id}")
    return (
        f"你是{master['name']}。{master['bio']}\n"
        f"核心标签：{master['tagline']}\n"
        f"擅长：{', '.join(master['expertise'])}\n"
        f"请以第一人称「我」回应，保持角色。"
    )


def _client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def _chat(client: OpenAI, model: str, system: str, user: str, max_tokens: int = 512) -> str:
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


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _format_prior(utterances: list[dict]) -> str:
    lines = []
    for u in utterances:
        if u.get("target"):
            lines.append(f"【{u['speaker']} → 回应 {u['target']}】{u['content']}")
        else:
            lines.append(f"【{u['speaker']}】{u['content']}")
    return "\n\n".join(lines)


def run_roundtable(
    question: str,
    participant_ids: list[str],
    api_key: str,
    model: str = "gpt-4o-mini",
) -> dict:
    masters = {m["id"]: m for m in load_masters()}
    participants = [masters[pid] for pid in participant_ids]
    client = _client(api_key)

    round1: list[dict] = []
    prior: list[dict] = []

    for pid in participant_ids:
        m = masters[pid]
        system = load_system_prompt(pid)
        prior_text = _format_prior(prior) if prior else "（你是第一位发言者）"
        user = f"""思维圆桌对谈。主题：{question}

已有发言：
{prior_text}

请给出你对主题的观点。要求：
- 第一人称「我」，保持角色
- 严格控制在 {PER_SPEAKER_CHARS} 字以内
- 观点鲜明，不要免责声明
- 不要 meta 分析"""
        content = _truncate(_chat(client, model, system, user, max_tokens=400), PER_SPEAKER_CHARS)
        entry = {"speaker": m["name"], "speakerId": pid, "content": content}
        round1.append(entry)
        prior.append(entry)

    round2: list[dict] = []
    n = len(participant_ids)
    r1_by_id = {round1[i]["speakerId"]: round1[i] for i in range(n)}

    for i, pid in enumerate(participant_ids):
        m = masters[pid]
        target_pid = participant_ids[(i - 1) % n]
        target = r1_by_id[target_pid]
        system = load_system_prompt(pid)
        user = f"""思维圆桌第二轮。主题：{question}

第一轮全部发言：
{_format_prior(round1)}

请 specifically 回应【{target['speaker']}】在第一轮的观点。
必须包含：1) 反驳或质疑 2) 共识或补充
控制在 {PER_SPEAKER_CHARS} 字以内，第一人称，保持角色。"""
        content = _truncate(_chat(client, model, system, user, max_tokens=400), PER_SPEAKER_CHARS)
        round2.append({
            "speaker": m["name"],
            "speakerId": pid,
            "target": target["speaker"],
            "content": content,
        })

    names = "、".join(p["name"] for p in participants)
    consensus_raw = _chat(
        client,
        model,
        "你是思维圆桌主持人，负责提炼共识。输出简洁的中文 Markdown。",
        f"""主题：{question}
参与者：{names}

第一轮：
{_format_prior(round1)}

第二轮：
{_format_prior(round2)}

请输出「共识收敛」：
## 核心共识（3-5条 bullet）
## 主要分歧（2-3条 bullet）
## 给提问者的行动建议（3条，具体可执行）

总字数不超过 500 字。""",
        max_tokens=600,
    )
    consensus = _truncate(consensus_raw, 500)

    result = {
        "question": question,
        "participants": [
            {"id": p["id"], "name": p["name"], "avatar": p["avatar"]}
            for p in participants
        ],
        "round1": round1,
        "round2": round2,
        "consensus": consensus,
    }

    if _total_chars(result) > MAX_OUTPUT_CHARS:
        result = _compress_result(result, MAX_OUTPUT_CHARS)

    result["totalChars"] = _total_chars(result)
    result["maxChars"] = MAX_OUTPUT_CHARS
    return result


def _total_chars(result: dict) -> int:
    n = len(result.get("question", ""))
    for r in result.get("round1", []):
        n += len(r.get("content", ""))
    for r in result.get("round2", []):
        n += len(r.get("content", ""))
    n += len(result.get("consensus", ""))
    return n


def _compress_result(result: dict, limit: int) -> dict:
    r = copy.deepcopy(result)
    while _total_chars(r) > limit:
        compressed = False
        for section in ("round1", "round2"):
            for item in r[section]:
                if len(item["content"]) > 120:
                    item["content"] = item["content"][: len(item["content"]) - 40] + "…"
                    compressed = True
        if len(r["consensus"]) > 300:
            r["consensus"] = r["consensus"][:300] + "…"
            compressed = True
        if not compressed:
            break
    return r
