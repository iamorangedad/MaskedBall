#!/usr/bin/env python3
"""MaskedBall web space.

Everyone is a node. A line appears between people after they talk.
A portrait in settings is the context used when a local model speaks for you.
"""

from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA_PATH = ROOT / "data" / "space.json"
HOST = os.environ.get("MASKEDBALL_HOST", "127.0.0.1")
PORT = int(os.environ.get("MASKEDBALL_PORT", "8787"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
MODEL = os.environ.get("MASKEDBALL_MODEL", "qwen3:4b")

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

LOCK = threading.Lock()

SEEDS = [
    {
        "id": "seed-linwan",
        "name": "林晚",
        "personality": "mysterious",
        "languageStyle": "poetic",
        "bio": "在城南旧戏园看过夜场的人。习惯把白天的事留到灯灭以后再说。",
        "keywords": ["夜色", "旧戏", "雨"],
        "greeting": "灯还没全亮。你也是这个时候才进来的吗？",
        "assistMode": "llm",
        "kind": "resident",
    },
    {
        "id": "seed-ahe",
        "name": "阿禾",
        "personality": "friendly",
        "languageStyle": "casual",
        "bio": "在花店打工，记得常客喜欢的花。说话先笑一下，再问你今天怎么样。",
        "keywords": ["花", "日常", "散步"],
        "greeting": "嘿，进来了？今天外面的风还算软。",
        "assistMode": "llm",
        "kind": "resident",
    },
    {
        "id": "seed-zhouheng",
        "name": "周衡",
        "personality": "academic",
        "languageStyle": "formal",
        "bio": "做文献编目的人。相信把一句话讲清楚，比把气氛做热更要紧。",
        "keywords": ["书", "编目", "提问"],
        "greeting": "你好。如果你愿意，我们可以从你真正想问的那句开始。",
        "assistMode": "llm",
        "kind": "resident",
    },
    {
        "id": "seed-xiaoman",
        "name": "小满",
        "personality": "humorous",
        "languageStyle": "internetSlang",
        "bio": "电台夜班的兼职主持。把尴尬的沉默当成可以接的梗。",
        "keywords": ["电台", "笑话", "夜宵"],
        "greeting": "来了啊。面具戴正了没？歪了也行，更好认。",
        "assistMode": "llm",
        "kind": "resident",
    },
    {
        "id": "seed-sucheng",
        "name": "苏澄",
        "personality": "creative",
        "languageStyle": "poetic",
        "bio": "给舞台画布景。看人的时候会先想，这个人适合站在什么颜色的光里。",
        "keywords": ["布景", "颜色", "舞台"],
        "greeting": "你站进来的那一下，灯光好像偏了一寸。",
        "assistMode": "llm",
        "kind": "resident",
    },
    {
        "id": "seed-chenyu",
        "name": "陈予",
        "personality": "supportive",
        "languageStyle": "casual",
        "bio": "在社区厨房帮忙。听人说话时会把杯子往对方那边推一点。",
        "keywords": ["厨房", "倾听", "热汤"],
        "greeting": "先坐下也行。不急着说，我在。",
        "assistMode": "llm",
        "kind": "resident",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seed_store() -> dict:
    conversations = {
        "seed-linwan|seed-sucheng": {
            "messages": [
                msg("seed-sucheng", "你站在廊柱边上的时候，影子比人先到。", "2026-04-02T13:10:00+00:00"),
                msg("seed-linwan", "影子比较诚实。人要等灯暗了才肯说话。", "2026-04-02T13:12:00+00:00"),
            ]
        },
        "seed-ahe|seed-xiaoman": {
            "messages": [
                msg("seed-xiaoman", "夜班结束想吃面，花店有没有能当夜宵的花？", "2026-04-03T15:02:00+00:00"),
                msg("seed-ahe", "没有。不过我可以告诉你哪家面还没打烊。", "2026-04-03T15:04:00+00:00"),
            ]
        },
        "seed-chenyu|seed-zhouheng": {
            "messages": [
                msg("seed-zhouheng", "你总把汤推过来。这是在打断我整理句子。", "2026-04-04T09:20:00+00:00"),
                msg("seed-chenyu", "句子可以等。汤凉了就不好听了。", "2026-04-04T09:22:00+00:00"),
            ]
        },
    }
    store = {"users": {s["id"]: dict(s) for s in SEEDS}, "conversations": conversations}
    return store


def msg(sender_id: str, content: str, created_at: str, via: str = "llm") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "senderId": sender_id,
        "content": content,
        "via": via,
        "createdAt": created_at,
    }


def load_store() -> dict:
    if not DATA_PATH.exists():
        store = seed_store()
        save_store(store)
        return store
    with DATA_PATH.open(encoding="utf-8") as handle:
        store = json.load(handle)
    changed = False
    for seed in SEEDS:
        if seed["id"] not in store["users"]:
            store["users"][seed["id"]] = dict(seed)
            changed = True
    store.setdefault("conversations", {})
    if changed:
        save_store(store)
    return store


def save_store(store: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(store, handle, ensure_ascii=False, indent=2)
    temporary.replace(DATA_PATH)


def conversation_key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def edges_from(store: dict) -> list[dict]:
    found = []
    for key, conversation in store["conversations"].items():
        messages = conversation.get("messages") or []
        if not messages or "|" not in key:
            continue
        left, right = key.split("|", 1)
        found.append({"a": left, "b": right, "messageCount": len(messages)})
    return found


def public_user(user: dict) -> dict:
    personality = PERSONALITIES.get(user["personality"], PERSONALITIES["friendly"])
    return {
        "id": user["id"],
        "name": user["name"],
        "personality": user["personality"],
        "personalityLabel": personality[0],
        "personalityHint": personality[1],
        "languageStyle": user["languageStyle"],
        "styleLabel": STYLES.get(user["languageStyle"], STYLES["casual"]),
        "bio": user["bio"],
        "keywords": user["keywords"],
        "greeting": user["greeting"],
        "assistMode": user["assistMode"],
        "kind": user["kind"],
    }


def catalog() -> dict:
    return {
        "personalities": [
            {"id": key, "label": label, "hint": hint}
            for key, (label, hint) in PERSONALITIES.items()
        ],
        "styles": [{"id": key, "label": label} for key, label in STYLES.items()],
        "model": MODEL,
    }


def clean_reply(name: str, text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    text = text.strip().strip("“”\"'「」")
    for prefix in (f"{name}：", f"{name}:", "短信：", "短信:"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def render_sms_prompt(speaker: dict, counterpart: dict, history: list[dict], hint: str) -> str:
    personality = PERSONALITIES.get(speaker["personality"], PERSONALITIES["friendly"])
    style = STYLES.get(speaker["languageStyle"], STYLES["casual"])
    keywords = "、".join(speaker["keywords"]) or "没有特别标明"
    lines = [
        f"你是{speaker['name']}。性格：{personality[0]}，{personality[1]}。",
        f"说话方式：{style}。",
        f"背景：{speaker['bio'] or '没有写背景'}。",
        f"在意：{keywords}。",
        f"你习惯这样开口：{speaker['greeting']}",
        f"你正在给{counterpart['name']}发短信。对方的背景：{counterpart['bio'] or '对方还没写背景'}。",
    ]
    if history:
        lines.append("已有对话：")
        names = {speaker["id"]: speaker["name"], counterpart["id"]: counterpart["name"]}
        for item in history[-8:]:
            lines.append(f"{names.get(item['senderId'], '对方')}：{item['content']}")
    else:
        lines.append("对话还没开始，请用你的方式打个招呼。")
    if hint:
        lines.append(f"这句想表达的意思：{hint}")
    lines.append("只写你的下一条短信，不超过40个字。不要解释，不要分析，不要加名字或引号。")
    body = "\n".join(lines)
    return f"<|im_start|>user\n{body}<|im_end|>\n<|im_start|>assistant\n短信："


def ollama_sms(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "raw": True,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.8,
            "num_predict": 80,
            "stop": ["<|im_end|>", "<|im_start|>", "\n"],
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL.replace("/api/chat", "/api/generate"),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise RuntimeError(f"模型请求失败：{detail or error.reason}") from error
    return data.get("response") or ""


def speak(speaker: dict, counterpart: dict, history: list[dict], hint: str = "") -> str:
    prompt = render_sms_prompt(speaker, counterpart, history, hint)
    text = clean_reply(speaker["name"], ollama_sms(prompt))
    if looks_like_reasoning(text):
        text = clean_reply(speaker["name"], ollama_sms(prompt + "直接写短信。"))
    if not text or looks_like_reasoning(text):
        raise RuntimeError("模型没有返回可发送的内容")
    return text


def looks_like_reasoning(text: str) -> bool:
    return text.startswith(("首先", "好的", "作为", "我需要", "用户", "短信")) or "不要解释" in text


def clip(value: str, limit: int) -> str:
    return value.strip()[:limit]


def normalize_profile(body: dict, current: dict) -> dict:
    name = clip(str(body.get("name", current["name"])), 20)
    if not name:
        raise ValueError("名字不能为空")
    personality = str(body.get("personality", current["personality"]))
    if personality not in PERSONALITIES:
        raise ValueError("未知的性格")
    style = str(body.get("languageStyle", current["languageStyle"]))
    if style not in STYLES:
        raise ValueError("未知的语言风格")
    assist = str(body.get("assistMode", current["assistMode"]))
    if assist not in ("llm", "human"):
        raise ValueError("未知的聊天方式")
    keywords = body.get("keywords", current["keywords"])
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.replace("，", ",").split(",")]
    if not isinstance(keywords, list):
        raise ValueError("关键词格式不对")
    clean_keywords = []
    for keyword in keywords:
        text = clip(str(keyword), 16)
        if text and text not in clean_keywords:
            clean_keywords.append(text)
        if len(clean_keywords) >= 12:
            break
    current["name"] = name
    current["personality"] = personality
    current["languageStyle"] = style
    current["bio"] = clip(str(body.get("bio", current["bio"])), 600)
    current["keywords"] = clean_keywords
    current["greeting"] = clip(str(body.get("greeting", current["greeting"])), 160)
    current["assistMode"] = assist
    return current


class Handler(BaseHTTPRequestHandler):
    server_version = "MaskedBall/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[web] {self.address_string()} {fmt % args}")

    def send_json(self, payload: dict, status: int = 200, cookie: str | None = None) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 100_000:
            raise ValueError("请求太大")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        data = json.loads(raw.decode())
        if not isinstance(data, dict):
            raise ValueError("请求格式不对")
        return data

    def user_id(self) -> str | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get("mb_id")
        if morsel is None:
            return None
        return morsel.value

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/space":
                self.handle_space()
                return
            if path.startswith("/api/chat/"):
                self.handle_get_chat(path[len("/api/chat/") :])
                return
            if path == "/api/health":
                self.handle_health()
                return
            self.handle_static(path)
        except ValueError as error:
            self.send_json({"error": str(error)}, 401)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/join":
                self.handle_join()
                return
            if path.startswith("/api/chat/"):
                self.handle_post_chat(path[len("/api/chat/") :])
                return
            self.send_json({"error": "没有这个接口"}, 404)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, 400)

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/me":
                self.handle_update_me()
                return
            self.send_json({"error": "没有这个接口"}, 404)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, 400)

    def handle_health(self) -> None:
        try:
            probe = urllib.request.Request(OLLAMA_URL.replace("/api/chat", "/api/tags"))
            with urllib.request.urlopen(probe, timeout=3) as response:
                ok = response.status == 200
        except (urllib.error.URLError, TimeoutError):
            ok = False
        self.send_json({"ok": ok, "model": MODEL})

    def handle_space(self) -> None:
        with LOCK:
            store = load_store()
            me_id = self.user_id()
            me = store["users"].get(me_id) if me_id else None
            users = [public_user(user) for user in store["users"].values()]
            payload = {
                "me": public_user(me) if me else None,
                "users": users,
                "edges": edges_from(store),
                "catalog": catalog(),
            }
        self.send_json(payload)

    def handle_join(self) -> None:
        body = self.read_json()
        name = clip(str(body.get("name", "")), 20) or "来客"
        with LOCK:
            store = load_store()
            existing_id = self.user_id()
            user = store["users"].get(existing_id) if existing_id else None
            if user is None or user.get("kind") != "guest":
                user = {
                    "id": "guest-" + uuid.uuid4().hex[:10],
                    "name": name,
                    "personality": "friendly",
                    "languageStyle": "casual",
                    "bio": "",
                    "keywords": [],
                    "greeting": "你好，我刚走进这个空间。",
                    "assistMode": "human",
                    "kind": "guest",
                }
                store["users"][user["id"]] = user
            else:
                user["name"] = name
            save_store(store)
            public = public_user(user)
            user_id = user["id"]
        cookie = f"mb_id={user_id}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000"
        self.send_json({"me": public}, cookie=cookie)

    def handle_update_me(self) -> None:
        body = self.read_json()
        with LOCK:
            store = load_store()
            user = self.require_me(store)
            normalize_profile(body, user)
            save_store(store)
            public = public_user(user)
        self.send_json({"me": public})

    def handle_get_chat(self, other_id: str) -> None:
        with LOCK:
            store = load_store()
            me = self.require_me(store)
            other = store["users"].get(other_id)
            if other is None or other["id"] == me["id"]:
                self.send_json({"error": "找不到这个人"}, 404)
                return
            key = conversation_key(me["id"], other_id)
            messages = list((store["conversations"].get(key) or {}).get("messages") or [])
        self.send_json({"messages": messages, "other": public_user(other)})

    def handle_post_chat(self, other_id: str) -> None:
        body = self.read_json()
        via = body.get("via", "human")
        if via not in ("human", "llm"):
            raise ValueError("未知的发送方式")
        content = clip(str(body.get("content", "")), 800)
        if via == "human" and not content:
            raise ValueError("消息不能为空")

        with LOCK:
            store = load_store()
            me = dict(self.require_me(store))
            other = store["users"].get(other_id)
            if other is None or other["id"] == me["id"]:
                self.send_json({"error": "找不到这个人"}, 404)
                return
            other = dict(other)
            key = conversation_key(me["id"], other["id"])
            history = list((store["conversations"].get(key) or {}).get("messages") or [])

        created: list[dict] = []
        reply_error = None
        try:
            if via == "llm":
                line = speak(me, other, history, content)
                created.append(msg(me["id"], line, now_iso(), "llm"))
            else:
                created.append(msg(me["id"], content, now_iso(), "human"))
        except (RuntimeError, urllib.error.URLError, TimeoutError, OSError) as error:
            self.send_json({"error": f"画像代聊没有完成：{error}"}, 502)
            return

        if other["assistMode"] == "llm":
            try:
                reply = speak(other, me, history + created)
                created.append(msg(other["id"], reply, now_iso(), "llm"))
            except (RuntimeError, urllib.error.URLError, TimeoutError, OSError) as error:
                reply_error = f"对方暂时没有接上：{error}"

        with LOCK:
            store = load_store()
            conversation = store["conversations"].setdefault(key, {"messages": []})
            conversation["messages"].extend(created)
            save_store(store)
            messages = list(conversation["messages"])
            edge = {"a": key.split("|")[0], "b": key.split("|")[1], "messageCount": len(messages)}
        self.send_json({"messages": messages, "edge": edge, "replyError": reply_error})

    def require_me(self, store: dict) -> dict:
        user = store["users"].get(self.user_id() or "")
        if user is None or user.get("kind") != "guest":
            raise ValueError("请先进入舞会")
        return user

    def handle_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        relative = path.lstrip("/")
        target = (STATIC / relative).resolve()
        if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
            self.send_error(404)
            return
        kind = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(target.suffix, "application/octet-stream")
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MaskedBall web  http://{HOST}:{PORT}", flush=True)
    print(f"模型  {MODEL}  via  {OLLAMA_URL}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
