"""Public cards versus the private background used only when a model speaks."""

from __future__ import annotations

import json

from maskedball import store
from maskedball.errors import AppError

PERSONALITIES = {
    "friendly": ("亲切", "温暖、好接近，愿意把话接住"),
    "humorous": ("幽默", "轻快，爱开无害的玩笑"),
    "mysterious": ("神秘", "话不多，留一点没说完的意思"),
    "academic": ("学究", "清楚、克制，喜欢把事情说准确"),
    "creative": ("灵动", "想象丰富，偶尔用比喻"),
    "supportive": ("体贴", "先接住对方的情绪，再轻轻回应"),
}
STYLES = {
    "formal": "正式，句子完整，不随便用语气词",
    "casual": "随意，像朋友发消息",
    "internetSlang": "轻松的网络口语，但不要堆砌表情",
    "poetic": "有一点诗意，句子短，意象干净",
    "technical": "具体、准确，少空话",
}


def catalog() -> dict:
    return {
        "personalities": [
            {"id": key, "label": label, "hint": hint}
            for key, (label, hint) in PERSONALITIES.items()
        ],
        "styles": [{"id": key, "label": label} for key, label in STYLES.items()],
    }


def _keywords(value, fallback: list[str]) -> list[str]:
    items = value if value is not None else fallback
    if isinstance(items, str):
        items = [part.strip() for part in items.replace("，", ",").split(",")]
    if not isinstance(items, list):
        raise AppError("关键词格式不对")
    cleaned = []
    for item in items:
        text = str(item).strip()[:16]
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= 12:
            break
    return cleaned


def update(user_id: str, body: dict) -> dict:
    current = store.fetch_user(user_id)
    if current is None or current["kind"] != "member":
        raise AppError("请先登录", 401)
    name = str(body.get("name", current["name"])).strip()[:20]
    if not name:
        raise AppError("名字不能为空")
    personality = str(body.get("personality", current["personality"]))
    if personality not in PERSONALITIES:
        raise AppError("未知的性格")
    style = str(body.get("languageStyle", current["languageStyle"]))
    if style not in STYLES:
        raise AppError("未知的语言风格")
    assist = str(body.get("assistMode", current["assistMode"]))
    if assist not in {"llm", "human"}:
        raise AppError("未知的聊天方式")
    keywords = _keywords(body.get("keywords", current["keywords"]), current["keywords"])
    bio = str(body.get("bio", current["bio"])).strip()[:600]
    greeting = str(body.get("greeting", current["greeting"])).strip()[:160]
    store.execute(
        """
        UPDATE users
        SET name=?, personality=?, language_style=?, bio=?, keywords=?, greeting=?, assist_mode=?
        WHERE id=?
        """,
        (
            name,
            personality,
            style,
            bio,
            json.dumps(keywords, ensure_ascii=False),
            greeting,
            assist,
            user_id,
        ),
    )
    updated = store.fetch_user(user_id)
    if updated is None:
        raise AppError("画像没有保存", 500)
    return updated


def public_card(user: dict, online: bool, unread: int = 0) -> dict:
    label, hint = PERSONALITIES[user["personality"]]
    return {
        "id": user["id"],
        "name": user["name"],
        "personality": user["personality"],
        "personalityLabel": label,
        "personalityHint": hint,
        "languageStyle": user["languageStyle"],
        "styleLabel": STYLES[user["languageStyle"]],
        "keywords": user["keywords"],
        "greeting": user["greeting"],
        "assistMode": user["assistMode"],
        "kind": user["kind"],
        "online": online,
        "unread": unread,
    }


def private_view(user: dict, online: bool, blocked: list[dict]) -> dict:
    card = public_card(user, online)
    card["bio"] = user["bio"]
    card["email"] = user["email"]
    card["blocked"] = blocked
    return card


def prompt_context(user: dict) -> dict:
    label, hint = PERSONALITIES[user["personality"]]
    return {
        "id": user["id"],
        "name": user["name"],
        "bio": user["bio"],
        "keywords": user["keywords"],
        "greeting": user["greeting"],
        "personalityLabel": label,
        "personalityHint": hint,
        "styleLabel": STYLES[user["languageStyle"]],
    }


def prompt_counterpart(user: dict) -> dict:
    context = prompt_context(user)
    context.pop("bio", None)
    return context
