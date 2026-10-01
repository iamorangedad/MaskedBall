"""One send turn: access check, optional generation, save, then notify."""

from __future__ import annotations

from maskedball import conversations, moderation, model, notify, portraits, presence, store
from maskedball.errors import AppError


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

    if other["assistMode"] == "llm":
        try:
            reply = model.submit(
                portraits.prompt_context(other),
                portraits.prompt_counterpart(viewer),
                history + created,
                "",
                quota_user=None,
            )
            created.append(_message(other["id"], reply, "llm"))
        except (AppError, RuntimeError, OSError, TimeoutError) as error:
            reply_error = f"对方暂时没有接上：{error}"

    conversations.append(viewer["id"], other["id"], created)
    conversations.mark_read(viewer["id"], other["id"])
    presence.touch(viewer["id"])
    _notify(viewer["id"], other["id"], created, reply_error)
    return {
        "messages": conversations.list_messages(viewer["id"], other["id"]),
        "edge": conversations.edge_between(viewer["id"], other["id"]),
        "replyError": reply_error,
    }
