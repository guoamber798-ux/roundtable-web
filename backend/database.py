"""TopTalk 用户与口令数据库（SQLite）"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "toptalk.db"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                credits INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS redeem_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                credits INTEGER NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 1,
                used_count INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code_id INTEGER NOT NULL,
                credits_granted INTEGER NOT NULL,
                redeemed_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (code_id) REFERENCES redeem_codes(id),
                UNIQUE(user_id, code_id)
            );
            """
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def seed_codes_from_env() -> None:
    raw = os.environ.get("INITIAL_CODES", "").strip()
    if not raw:
        return
    with get_conn() as conn:
        for part in raw.split(","):
            part = part.strip()
            if not part or ":" not in part:
                continue
            code, credits_s = part.split(":", 1)
            code = code.strip().upper()
            try:
                credits = int(credits_s.strip())
            except ValueError:
                continue
            exists = conn.execute(
                "SELECT id FROM redeem_codes WHERE code = ?", (code,)
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT INTO redeem_codes (code, credits, max_uses, created_at) VALUES (?, ?, 999, ?)",
                    (code, credits, _now()),
                )


def create_user(username: str, password_hash: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, credits, created_at) VALUES (?, ?, 0, ?)",
            (username, password_hash, _now()),
        )
        return cur.lastrowid


def get_user_by_username(username: str) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def deduct_credit(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT credits FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row or row["credits"] < 1:
            return False
        conn.execute(
            "UPDATE users SET credits = credits - 1 WHERE id = ? AND credits >= 1",
            (user_id,),
        )
        return True


def redeem_code(user_id: int, code: str) -> tuple[int, str]:
    code = normalize_code(code)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM redeem_codes WHERE code = ? AND active = 1", (code,)
        ).fetchone()
        if not row:
            return 0, "口令无效或已失效"
        if row["used_count"] >= row["max_uses"]:
            return 0, "该口令已达使用上限"

        already = conn.execute(
            "SELECT id FROM redemptions WHERE user_id = ? AND code_id = ?",
            (user_id, row["id"]),
        ).fetchone()
        if already:
            return 0, "你已使用过该口令"

        credits = row["credits"]
        conn.execute(
            "UPDATE users SET credits = credits + ? WHERE id = ?",
            (credits, user_id),
        )
        conn.execute(
            "UPDATE redeem_codes SET used_count = used_count + 1 WHERE id = ?",
            (row["id"],),
        )
        conn.execute(
            "INSERT INTO redemptions (user_id, code_id, credits_granted, redeemed_at) VALUES (?, ?, ?, ?)",
            (user_id, row["id"], credits, _now()),
        )
        return credits, f"成功兑换 {credits} 次领晤机会"


def normalize_code(code: str) -> str:
    return code.strip().upper()


def admin_create_code(code: str, credits: int, max_uses: int = 1) -> bool:
    """创建或更新口令，返回 True 表示新建，False 表示更新已有口令。"""
    code = normalize_code(code)
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT id FROM redeem_codes WHERE code = ?", (code,)
        ).fetchone()
        conn.execute(
            """INSERT INTO redeem_codes (code, credits, max_uses, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(code) DO UPDATE SET credits=excluded.credits, max_uses=excluded.max_uses, active=1""",
            (code, credits, max_uses, _now()),
        )
        return exists is None


def admin_create_codes_batch(
    codes: list[str], credits: int, max_uses: int = 1
) -> dict:
    created = 0
    updated = 0
    items: list[str] = []
    for raw in codes:
        code = normalize_code(raw)
        if not code:
            continue
        if admin_create_code(code, credits, max_uses):
            created += 1
        else:
            updated += 1
        items.append(code)
    return {"created": created, "updated": updated, "codes": items}


def generate_codes(count: int, credits: int, prefix: str = "TT") -> list[str]:
    import secrets

    prefix = normalize_code(prefix)
    codes: list[str] = []
    with get_conn() as conn:
        while len(codes) < count:
            code = f"{prefix}-{secrets.token_hex(8).upper()}"
            exists = conn.execute(
                "SELECT id FROM redeem_codes WHERE code = ?", (code,)
            ).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT INTO redeem_codes (code, credits, max_uses, created_at) VALUES (?, ?, 1, ?)",
                (code, credits, _now()),
            )
            codes.append(code)
    return codes
