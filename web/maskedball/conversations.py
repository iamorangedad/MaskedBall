"""Messages and read cursors. Only the two participants can read a thread."""

from __future__ import annotations

from maskedball import store
from maskedball.errors import AppError


def conversation_id(left_id: str, right_id: str) -> str:
    return "|".join(sorted((left_id, right_id)))


def _require_other(viewer_id: str, other_id: str) -> dict:
    if viewer_id == other_id:
        raise AppError("找不到这个人", 404)
    other = store.fetch_user(other_id)
    if other is None:
        raise AppError("找不到这个人", 404)
    return other


def list_messages(viewer_id: str, other_id: str) -> list[dict]:
    _require_other(viewer_id, other_id)
    key = conversation_id(viewer_id, other_id)
    rows = store.query(
        """
        SELECT id, sender_id, content, via, created_at
        FROM messages WHERE conversation_id=?
        ORDER BY created_at, rowid
        """,
        (key,),
    )
    return [
        {
            "id": row["id"],
            "senderId": row["sender_id"],
            "content": row["content"],
            "via": row["via"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def mark_read(viewer_id: str, other_id: str) -> None:
    _require_other(viewer_id, other_id)
    key = conversation_id(viewer_id, other_id)
    store.execute(
        """
        INSERT INTO reads (user_id, conversation_id, last_read_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, conversation_id) DO UPDATE SET last_read_at=excluded.last_read_at
        """,
        (viewer_id, key, store.now_iso()),
    )


def unread(viewer_id: str, other_id: str) -> int:
    key = conversation_id(viewer_id, other_id)
    rows = store.query(
        """
        SELECT COUNT(*) AS n FROM messages
        WHERE conversation_id=? AND sender_id!=?
        AND created_at > COALESCE(
            (SELECT last_read_at FROM reads WHERE user_id=? AND conversation_id=?),
            ''
        )
        """,
        (key, viewer_id, viewer_id, key),
    )
    return int(rows[0]["n"])


def append(viewer_id: str, other_id: str, messages: list[dict]) -> None:
    if not messages:
        return
    key = conversation_id(viewer_id, other_id)
    pair = tuple(sorted((viewer_id, other_id)))

    def run(conn) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO conversations (id, user_a, user_b, created_at) VALUES (?, ?, ?, ?)",
            (key, pair[0], pair[1], messages[0]["createdAt"]),
        )
        for message in messages:
            conn.execute(
                """
                INSERT INTO messages (id, conversation_id, sender_id, content, via, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message["id"],
                    key,
                    message["senderId"],
                    message["content"],
                    message["via"],
                    message["createdAt"],
                ),
            )

    store.transaction(run)


def edge_between(viewer_id: str, other_id: str) -> dict | None:
    key = conversation_id(viewer_id, other_id)
    rows = store.query(
        "SELECT COUNT(*) AS n FROM messages WHERE conversation_id=?",
        (key,),
    )
    count = int(rows[0]["n"])
    if count == 0:
        return None
    pair = key.split("|")
    return {
        "a": pair[0],
        "b": pair[1],
        "messageCount": count,
        "unread": unread(viewer_id, other_id),
    }


def edges_for(viewer_id: str) -> list[dict]:
    rows = store.query(
        """
        SELECT c.user_a, c.user_b, COUNT(m.id) AS n
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id
        GROUP BY c.id
        """
    )
    kinds = {user["id"]: user["kind"] for user in store.list_users()}
    edges = []
    for row in rows:
        if int(row["n"]) == 0:
            continue
        left, right = row["user_a"], row["user_b"]
        both_residents = kinds.get(left) == "resident" and kinds.get(right) == "resident"
        if viewer_id not in (left, right) and not both_residents:
            continue
        other = right if left == viewer_id else left if right == viewer_id else None
        edges.append(
            {
                "a": left,
                "b": right,
                "messageCount": int(row["n"]),
                "unread": unread(viewer_id, other) if other else 0,
            }
        )
    return edges
