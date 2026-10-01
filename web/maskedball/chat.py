"""One send turn: access check, optional generation, save, then notify.

The other person's portrait reply is generated after the send returns, so the
sender can post again without waiting for that reply.
"""

from __future__ import annotations

import threading

from maskedball import conversations, moderation, model, notify, portraits, presence, store
from maskedball.errors import AppError

_reply_locks: dict[str, threading.Lock] = {}
_reply_guard = threading.Lock()


def _message(sender_id: str, content: str, via: str) -> dict:
    return {
        "id": store.new_id("msg-"),
        "senderId": sender_id,
        "content": content,
        "via": via,
        "createdAt": store.now_iso(),
    }


def _notify(viewer_id: str, other_id: str, created: list[dict], reply_error: str | None) -> None:
    for user_id, other in ((viewer_id, other_id), (other_id, viewer_id)):
        notify.publish(
            user_id,
            "chat",
            {
                "otherId": other,
                "messages": created,
                "unread": conversations.unread(user_id, other),
                "edge": conversations.edge_between(user_id, other),
                "replyError": reply_error,
            },
        )


def post(viewer: dict, other_id: str, via: str, content: str) -> dict:
    if via not in {"human", "llm"}:
        raise AppError("未知的发送方式")
    other = store.fetch_user(other_id)
    if other is None or other["id"] == viewer["id"]:
        raise AppError("找不到这个人", 404)
    if moderation.is_blocked(viewer["id"], other["id"]):
        raise AppError("你们之间现在不能发消息", 403)
    text = content.strip()[:800]
    if via == "human" and not text:
        raise AppError("消息不能为空")

    history = conversations.list_messages(viewer["id"], other["id"])
    created: list[dict] = []
    reply_error = None
    try:
        if via == "llm":
            line = model.submit(
                portraits.prompt_context(viewer),
                portraits.prompt_counterpart(other),
                history,
                text,
                quota_user=viewer["id"],
            )
            created.append(_message(viewer["id"], line, "llm"))
        else:
            created.append(_message(viewer["id"], text, "human"))
    except AppError:
        raise
    except (RuntimeError, OSError, TimeoutError) as error:
        raise AppError(f"画像代聊没有完成：{error}", 502) from error

    conversations.append(viewer["id"], other["id"], created)
    conversations.mark_read(viewer["id"], other["id"])
    presence.touch(viewer["id"])
    _notify(viewer["id"], other["id"], created, reply_error)
    if other["assistMode"] == "llm":
        _schedule_reply(viewer["id"], other["id"])
    return {
        "messages": conversations.list_messages(viewer["id"], other["id"]),
        "edge": conversations.edge_between(viewer["id"], other["id"]),
        "replyError": reply_error,
    }


def _conversation_lock(left_id: str, right_id: str) -> threading.Lock:
    key = conversations.conversation_id(left_id, right_id)
    with _reply_guard:
        lock = _reply_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _reply_locks[key] = lock
        return lock


def _schedule_reply(viewer_id: str, other_id: str) -> None:
    threading.Thread(
        target=_reply_later,
        args=(viewer_id, other_id),
        name="maskedball-reply",
        daemon=True,
    ).start()


def _reply_later(viewer_id: str, other_id: str) -> None:
    """Answer the latest messages. A burst sent during generation gets another pass."""
    with _conversation_lock(viewer_id, other_id):
        answered: set[str] = set()
        first = True
        while True:
            viewer = store.fetch_user(viewer_id)
            other = store.fetch_user(other_id)
            if viewer is None or other is None or other["assistMode"] != "llm":
                return
            if moderation.is_blocked(viewer_id, other_id):
                return
            history = conversations.list_messages(viewer_id, other_id)
            if first:
                if not history or history[-1]["senderId"] != viewer_id:
                    return
                last_other = max(
                    (index for index, item in enumerate(history) if item["senderId"] != viewer_id),
                    default=-1,
                )
                answered.update(
                    item["id"] for item in history[: last_other + 1] if item["senderId"] == viewer_id
                )
                first = False
            pending = [item for item in history if item["senderId"] == viewer_id and item["id"] not in answered]
            if not pending:
                return
            seen = {item["id"] for item in history}
            try:
                reply = model.submit(
                    portraits.prompt_context(other),
                    portraits.prompt_counterpart(viewer),
                    history,
                    "",
                    quota_user=None,
                )
            except (AppError, RuntimeError, OSError, TimeoutError) as error:
                _notify(viewer_id, other_id, [], f"对方暂时没有接上：{error}")
                return
            created = [_message(other_id, reply, "llm")]
            conversations.append(viewer_id, other_id, created)
            _notify(viewer_id, other_id, created, None)
            answered.update(item["id"] for item in history if item["senderId"] == viewer_id)
            latest = conversations.list_messages(viewer_id, other_id)
            if not any(item["senderId"] == viewer_id and item["id"] not in seen for item in latest):
                return
