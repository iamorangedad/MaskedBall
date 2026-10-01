"""Queued local generation. Callers pass portrait context in; this module never reads SQL."""

from __future__ import annotations

import json
import queue
import re
import threading
import time
import urllib.error
import urllib.request

from maskedball import config
from maskedball.errors import AppError

_jobs: queue.Queue = queue.Queue(maxsize=8)
_started = False
_quota: dict[str, list[float]] = {}
_quota_lock = threading.Lock()


def enforce_quota(user_id: str) -> None:
    limit = config.llm_quota()
    now = time.time()
    with _quota_lock:
        recent = [stamp for stamp in _quota.get(user_id, []) if now - stamp < 3600]
        if len(recent) >= limit:
            _quota[user_id] = recent
            raise AppError("这一小时的代聊次数用完了", 429)
        recent.append(now)
        _quota[user_id] = recent


def _release_quota(user_id: str) -> None:
    with _quota_lock:
        stamps = _quota.get(user_id, [])
        if stamps:
            stamps.pop()


def build_prompt(speaker: dict, counterpart: dict, history: list[dict], hint: str) -> str:
    keywords = "、".join(speaker.get("keywords") or []) or "没有特别标明"
    their_keywords = "、".join(counterpart.get("keywords") or []) or "没有特别标明"
    lines = [
        f"你是{speaker['name']}。性格：{speaker['personalityLabel']}，{speaker['personalityHint']}。",
        f"说话方式：{speaker['styleLabel']}。",
        f"背景：{speaker.get('bio') or '没有写背景'}。",
        f"在意：{keywords}。",
        f"你习惯这样开口：{speaker.get('greeting') or ''}",
        (
            f"你正在给{counterpart['name']}发短信。"
            f"对方的公开印象：{counterpart['personalityLabel']}，在意{their_keywords}。"
        ),
        "不要索要密码、住址、证件或付款。不要替本人承诺见面、交易或转账。",
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


def _looks_like_reasoning(text: str) -> bool:
    return text.startswith(("首先", "好的", "作为", "我需要", "用户", "短信")) or "不要解释" in text


def clean_reply(name: str, text: str) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    text = text.strip().strip("“”\"'「」")
    for prefix in (f"{name}：", f"{name}:", "短信：", "短信:"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    return re.sub(r"\s+", " ", text).strip()[:500]


def _generate(prompt: str) -> str:
    payload = {
        "model": config.model_name(),
        "prompt": prompt,
        "raw": True,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0.8, "num_predict": 80, "stop": ["<|im_end|>", "<|im_start|>", "\n"]},
    }
    request = urllib.request.Request(
        config.ollama_url(),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=config.llm_timeout()) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise RuntimeError(f"模型请求失败：{detail or error.reason}") from error
    return data.get("response") or ""


def _complete(speaker: dict, counterpart: dict, history: list[dict], hint: str) -> str:
    prompt = build_prompt(speaker, counterpart, history, hint)
    text = clean_reply(speaker["name"], _generate(prompt))
    if _looks_like_reasoning(text):
        text = clean_reply(speaker["name"], _generate(prompt + "直接写短信。"))
    if not text or _looks_like_reasoning(text):
        raise RuntimeError("模型没有返回可发送的内容")
    return text


def _worker() -> None:
    while True:
        job = _jobs.get()
        try:
            job()
        except Exception:
            pass
        finally:
            _jobs.task_done()


def start() -> None:
    global _started
    if _started:
        return
    threading.Thread(target=_worker, name="maskedball-model", daemon=True).start()
    _started = True


def submit(speaker: dict, counterpart: dict, history: list[dict], hint: str, quota_user: str | None) -> str:
    if quota_user:
        enforce_quota(quota_user)
    holder: dict = {"event": threading.Event(), "result": None, "error": None}

    def job() -> None:
        try:
            holder["result"] = _complete(speaker, counterpart, history, hint)
        except Exception as error:
            holder["error"] = error
        finally:
            holder["event"].set()

    try:
        _jobs.put_nowait(job)
    except queue.Full:
        if quota_user:
            _release_quota(quota_user)
        raise AppError("模型正忙，请稍后再试", 429) from None
    if not holder["event"].wait(config.llm_timeout()):
        raise AppError("模型超时", 504)
    if holder["error"] is not None:
        if isinstance(holder["error"], AppError):
            raise holder["error"]
        raise RuntimeError(str(holder["error"]))
    return holder["result"]


def health() -> dict:
    ok = False
    try:
        probe = config.ollama_url().rsplit("/", 1)[0] + "/tags"
        with urllib.request.urlopen(probe, timeout=3) as response:
            ok = response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        ok = False
    return {"ok": ok, "model": config.model_name(), "queued": _jobs.qsize()}
