"""Who has been active recently. Residents in model mode stay available."""

from __future__ import annotations

from datetime import datetime, timezone

from maskedball import store

ONLINE_SECONDS = 45


def touch(user_id: str) -> None:
    store.execute(
        "UPDATE users SET last_seen_at=? WHERE id=?",
        (store.now_iso(), user_id),
    )


def online(user: dict) -> bool:
    if user["kind"] == "resident" and user["assistMode"] == "llm":
        return True
    seen = user.get("lastSeenAt")
    if not seen:
        return False
    moment = datetime.fromisoformat(seen)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - moment).total_seconds() <= ONLINE_SECONDS
