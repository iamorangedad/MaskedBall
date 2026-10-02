"""Send one line, then let portraits keep the conversation going.

A person in portrait mode keeps sending and answering until they switch back
to writing by hand. The send itself returns before those later turns.
"""

from __future__ import annotations

import threading

from maskedball import conversations, moderation, model, notify, portraits, presence, store
from maskedball.errors import AppError

_reply_locks: dict[str, threading.Lock] = {}
_running: set[str] = set()
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
    _schedule_continue(viewer["id"], other["id"], None)
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


def resume(viewer: dict, other_id: str) -> dict:
    """Keep going if either person is still letting their portrait speak."""
    other = store.fetch_user(other_id)
    if other is None or other["id"] == viewer["id"]:
        raise AppError("找不到这个人", 404)
    if moderation.is_blocked(viewer["id"], other["id"]):
        raise AppError("你们之间现在不能发消息", 403)
    history = conversations.list_messages(viewer["id"], other["id"])
    if _next_turn(history, viewer, other, viewer["id"]) is not None:
        _schedule_continue(viewer["id"], other["id"], viewer["id"])
    return {
        "messages": history,
        "edge": conversations.edge_between(viewer["id"], other["id"]),
    }


def _schedule_continue(left_id: str, right_id: str, opener_id: str | None) -> None:
    key = conversations.conversation_id(left_id, right_id)
    with _reply_guard:
        if key in _running:
            return
        _running.add(key)
    threading.Thread(
        target=_continue_later,
        args=(left_id, right_id, opener_id),
        name="maskedball-reply",
        daemon=True,
    ).start()


def _next_turn(history: list[dict], left: dict | None, right: dict | None, opener_id: str | None):
    if left is None or right is None or moderation.is_blocked(left["id"], right["id"]):
        return None
    if not history:
        opener = left if left["id"] == opener_id else right if right["id"] == opener_id else None
        if opener is None or opener["assistMode"] != "llm":
            return None
        listener = right if opener is left else left
        return opener, listener
    speaker, listener = (right, left) if history[-1]["senderId"] == left["id"] else (left, right)
    if history[-1]["senderId"] not in {left["id"], right["id"]} or speaker["assistMode"] != "llm":
        return None
    return speaker, listener


def _speak(speaker: dict, listener: dict, history: list[dict]) -> str | None:
    quota = speaker["id"] if speaker.get("kind") == "member" else None
    try:
        return model.submit(
            portraits.prompt_context(speaker),
            portraits.prompt_counterpart(listener),
            history,
            "",
            quota_user=quota,
        )
    except (AppError, RuntimeError, OSError, TimeoutError) as error:
        _notify(speaker["id"], listener["id"], [], f"画像代聊停住了：{error}")
        return None


def _continue_later(left_id: str, right_id: str, opener_id: str | None) -> None:
    """Whoever is in portrait mode speaks next, including the person who just enabled it."""
    key = conversations.conversation_id(left_id, right_id)
    clean = False
    try:
        with _conversation_lock(left_id, right_id):
            while True:
                left = store.fetch_user(left_id)
                right = store.fetch_user(right_id)
                history = conversations.list_messages(left_id, right_id) if left and right else []
                turn = _next_turn(history, left, right, opener_id if not history else None)
                if turn is None:
                    clean = True
                    return
                speaker, listener = turn
                while True:
                    seen = {item["id"] for item in history}
                    line = _speak(speaker, listener, history)
                    if line is None:
                        return
                    created = [_message(speaker["id"], line, "llm")]
                    conversations.append(speaker["id"], listener["id"], created)
                    _notify(speaker["id"], listener["id"], created, None)
                    latest = conversations.list_messages(left_id, right_id)
                    if not any(item["senderId"] == listener["id"] and item["id"] not in seen for item in latest):
                        break
                    history = latest
                    speaker = store.fetch_user(speaker["id"]) or speaker
                    listener = store.fetch_user(listener["id"]) or listener
                    if speaker["assistMode"] != "llm":
                        clean = True
                        return
    finally:
        with _reply_guard:
            _running.discard(key)
        if clean:
            left = store.fetch_user(left_id)
            right = store.fetch_user(right_id)
            history = conversations.list_messages(left_id, right_id) if left and right else []
            if _next_turn(history, left, right, None) is not None:
                _schedule_continue(left_id, right_id, None)
