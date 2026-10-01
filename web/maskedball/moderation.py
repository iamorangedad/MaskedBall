"""Blocks and reports. This module does not send messages."""

from __future__ import annotations

from maskedball import store
from maskedball.errors import AppError


def block(blocker_id: str, blocked_id: str) -> None:
    if blocker_id == blocked_id or store.fetch_user(blocked_id) is None:
        raise AppError("找不到这个人", 404)
    store.execute(
        """
        INSERT OR IGNORE INTO blocks (blocker_id, blocked_id, created_at)
        VALUES (?, ?, ?)
        """,
        (blocker_id, blocked_id, store.now_iso()),
    )


def unblock(blocker_id: str, blocked_id: str) -> None:
    store.execute(
        "DELETE FROM blocks WHERE blocker_id=? AND blocked_id=?",
        (blocker_id, blocked_id),
    )


def is_blocked(left_id: str, right_id: str) -> bool:
    rows = store.query(
        """
        SELECT 1 AS found FROM blocks
        WHERE (blocker_id=? AND blocked_id=?) OR (blocker_id=? AND blocked_id=?)
        LIMIT 1
        """,
        (left_id, right_id, right_id, left_id),
    )
    return bool(rows)


def ids_blocked_by(user_id: str) -> set[str]:
    rows = store.query("SELECT blocked_id FROM blocks WHERE blocker_id=?", (user_id,))
    return {row["blocked_id"] for row in rows}


def blocked_people(user_id: str) -> list[dict]:
    rows = store.query(
        """
        SELECT u.id, u.name FROM blocks b
        JOIN users u ON u.id = b.blocked_id
        WHERE b.blocker_id=?
        ORDER BY u.name
        """,
        (user_id,),
    )
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def report(reporter_id: str, target_id: str, reason: str) -> None:
    text = reason.strip()[:300]
    if reporter_id == target_id or store.fetch_user(target_id) is None:
        raise AppError("找不到这个人", 404)
    if len(text) < 2:
        raise AppError("请写明原因")
    store.execute(
        """
        INSERT INTO reports (id, reporter_id, target_id, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (store.new_id("report-"), reporter_id, target_id, text, store.now_iso()),
    )
