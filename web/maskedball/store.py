"""SQLite persistence and backups. No registration or chat rules live here."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from maskedball import config
from maskedball.seeds import THREADS, USERS

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    personality TEXT NOT NULL,
    language_style TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '[]',
    greeting TEXT NOT NULL DEFAULT '',
    assist_mode TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_a TEXT NOT NULL,
    user_b TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    content TEXT NOT NULL,
    via TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reads (
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    last_read_at TEXT NOT NULL,
    PRIMARY KEY (user_id, conversation_id)
);
CREATE TABLE IF NOT EXISTS blocks (
    blocker_id TEXT NOT NULL,
    blocked_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (blocker_id, blocked_id)
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    reporter_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_conversation ON messages (conversation_id, created_at);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:10]


def init() -> None:
    global _conn
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        if _conn is not None:
            _conn.close()
        connection = sqlite3.connect(path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.executescript(SCHEMA)
        connection.commit()
        _conn = connection


def connection() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("数据库还没有初始化")
    return _conn


def query(sql: str, params: tuple = ()) -> list[dict]:
    with _lock:
        rows = connection().execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def execute(sql: str, params: tuple = ()) -> None:
    with _lock:
        connection().execute(sql, params)
        connection().commit()


def transaction(fn):
    with _lock:
        conn = connection()
        try:
            result = fn(conn)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def user_from_row(row: dict) -> dict:
    data = dict(row)
    data.pop("password_hash", None)
    data["keywords"] = json.loads(data.pop("keywords") or "[]")
    data["languageStyle"] = data.pop("language_style")
    data["assistMode"] = data.pop("assist_mode")
    data["createdAt"] = data.pop("created_at")
    data["lastSeenAt"] = data.pop("last_seen_at")
    return data


def fetch_user(user_id: str) -> dict | None:
    rows = query("SELECT * FROM users WHERE id=?", (user_id,))
    if not rows:
        return None
    return user_from_row(rows[0])


def list_users() -> list[dict]:
    return [user_from_row(row) for row in query("SELECT * FROM users ORDER BY name")]


def seed() -> None:
    created = now_iso()

    def run(conn: sqlite3.Connection) -> None:
        for user in USERS:
            conn.execute(
                """
                INSERT OR IGNORE INTO users (
                    id, email, name, password_hash, personality, language_style, bio,
                    keywords, greeting, assist_mode, kind, created_at
                ) VALUES (?, NULL, ?, '', ?, ?, ?, ?, ?, ?, 'resident', ?)
                """,
                (
                    user["id"],
                    user["name"],
                    user["personality"],
                    user["language_style"],
                    user["bio"],
                    json.dumps(user["keywords"], ensure_ascii=False),
                    user["greeting"],
                    user["assist_mode"],
                    created,
                ),
            )
        count = conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
        if count:
            return
        for left, right, thread in THREADS:
            pair = tuple(sorted((left, right)))
            conversation_id = "|".join(pair)
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, user_a, user_b, created_at) VALUES (?, ?, ?, ?)",
                (conversation_id, pair[0], pair[1], thread[0][2]),
            )
            for sender_id, content, created_at in thread:
                conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, sender_id, content, via, created_at)
                    VALUES (?, ?, ?, ?, 'llm', ?)
                    """,
                    (new_id("msg-"), conversation_id, sender_id, content, created_at),
                )

    transaction(run)


def backup_once() -> Path | None:
    folder = config.backup_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = folder / f"space-{stamp}.sqlite"
    with _lock:
        dest = sqlite3.connect(target)
        try:
            connection().backup(dest)
        finally:
            dest.close()
    kept = sorted(folder.glob("space-*.sqlite"))
    for stale in kept[:-7]:
        stale.unlink(missing_ok=True)
    return target
