"""Identity: passwords, sessions, and reset codes. Profiles and messages stay elsewhere."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import smtplib
import time
from datetime import timedelta
from email.message import EmailMessage

from maskedball import config, store
from maskedball.errors import AppError

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_failures: dict[str, list[float]] = {}
_SESSION_DAYS = 30
_RESET_MINUTES = 20
_FAILURE_WINDOW = 600
_FAILURE_LIMIT = 8


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$", 2)
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not _EMAIL.match(cleaned) or len(cleaned) > 120:
        raise AppError("邮箱格式不对")
    return cleaned


def _check_password(password: str) -> str:
    if len(password) < 8 or len(password) > 200:
        raise AppError("密码至少 8 位")
    return password


def _check_name(name: str) -> str:
    cleaned = name.strip()[:20]
    if not cleaned:
        raise AppError("名字不能为空")
    return cleaned


def _too_many_failures(email: str) -> bool:
    now = time.time()
    recent = [stamp for stamp in _failures.get(email, []) if now - stamp < _FAILURE_WINDOW]
    _failures[email] = recent
    return len(recent) >= _FAILURE_LIMIT


def _note_failure(email: str) -> None:
    _failures.setdefault(email, []).append(time.time())


def _clear_failures(email: str) -> None:
    _failures.pop(email, None)


def _later(minutes: int = 0, days: int = 0) -> str:
    moment = store.now_iso()
    base = moment
    from datetime import datetime

    current = datetime.fromisoformat(base)
    return (current + timedelta(days=days, minutes=minutes)).isoformat(timespec="seconds")


def register(email: str, name: str, password: str) -> dict:
    cleaned_email = _normalize_email(email)
    cleaned_name = _check_name(name)
    checked = _check_password(password)
    existing = store.query("SELECT id FROM users WHERE email=?", (cleaned_email,))
    if existing:
        raise AppError("这个邮箱已经注册")
    user_id = store.new_id("member-")
    created = store.now_iso()
    store.execute(
        """
        INSERT INTO users (
            id, email, name, password_hash, personality, language_style, bio,
            keywords, greeting, assist_mode, kind, created_at
        ) VALUES (?, ?, ?, ?, 'friendly', 'casual', '', '[]', ?, 'human', 'member', ?)
        """,
        (
            user_id,
            cleaned_email,
            cleaned_name,
            _hash_password(checked),
            "你好，我刚走进这个空间。",
            created,
        ),
    )
    user = store.fetch_user(user_id)
    if user is None:
        raise AppError("注册没有完成", 500)
    return user


def _password_hash(user_id: str) -> str:
    rows = store.query("SELECT password_hash FROM users WHERE id=?", (user_id,))
    if not rows:
        return ""
    return rows[0]["password_hash"]


def authenticate(email: str, password: str) -> dict:
    cleaned = email.strip().lower()
    if _too_many_failures(cleaned):
        raise AppError("尝试太多次了，请稍后再登录", 429)
    rows = store.query("SELECT * FROM users WHERE email=?", (cleaned,))
    if not rows or not _verify_password(password, rows[0]["password_hash"]):
        _note_failure(cleaned)
        raise AppError("邮箱或密码不对", 401)
    _clear_failures(cleaned)
    return store.user_from_row(rows[0])


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    store.execute(
        """
        INSERT INTO sessions (token_hash, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (_token_hash(token), user_id, store.now_iso(), _later(days=_SESSION_DAYS)),
    )
    return token


def revoke_token(token: str) -> None:
    if not token:
        return
    store.execute(
        "UPDATE sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
        (store.now_iso(), _token_hash(token)),
    )


def revoke_user_sessions(user_id: str) -> None:
    store.execute(
        "UPDATE sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
        (store.now_iso(), user_id),
    )


def user_for_token(token: str | None) -> dict | None:
    if not token:
        return None
    rows = store.query(
        """
        SELECT u.* FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at > ?
        """,
        (_token_hash(token), store.now_iso()),
    )
    if not rows:
        return None
    return store.user_from_row(rows[0])


def change_password(user_id: str, current: str, new_password: str) -> str:
    checked = _check_password(new_password)
    if not _verify_password(current, _password_hash(user_id)):
        raise AppError("当前密码不对", 401)
    store.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (_hash_password(checked), user_id),
    )
    revoke_user_sessions(user_id)
    return create_session(user_id)


def _store_reset(user_id: str) -> str:
    code = secrets.token_hex(4)
    store.execute(
        """
        INSERT INTO password_resets (token_hash, user_id, expires_at)
        VALUES (?, ?, ?)
        """,
        (_token_hash(code), user_id, _later(minutes=_RESET_MINUTES)),
    )
    return code


def _send_code(email: str, code: str) -> bool:
    settings = config.smtp()
    if settings is None:
        return False
    message = EmailMessage()
    message["Subject"] = "假面舞会重置码"
    message["From"] = settings["from"]
    message["To"] = email
    message.set_content(f"重置码是 {code} ，20 分钟内有效。如果不是你本人操作，忽略这封信。")
    with smtplib.SMTP(settings["host"], settings["port"], timeout=15) as client:
        client.starttls()
        if settings["user"]:
            client.login(settings["user"], settings["password"])
        client.send_message(message)
    return True


def request_reset(email: str) -> str:
    """Always returns the same delivery channel name, whether or not the mailbox exists."""
    delivery = "email" if config.smtp() else "operator"
    rows = store.query("SELECT id FROM users WHERE email=?", (email.strip().lower(),))
    if not rows:
        return delivery
    code = _store_reset(rows[0]["id"])
    if delivery == "email":
        try:
            _send_code(email.strip().lower(), code)
        except (OSError, smtplib.SMTPException) as error:
            raise AppError(f"重置信没有发出去：{error}", 502) from error
    return delivery


def issue_reset(email: str) -> str:
    rows = store.query("SELECT id FROM users WHERE email=?", (email.strip().lower(),))
    if not rows:
        raise AppError("没有这个邮箱")
    return _store_reset(rows[0]["id"])


def reset_password(email: str, code: str, new_password: str) -> None:
    checked = _check_password(new_password)
    rows = store.query(
        """
        SELECT r.token_hash, r.user_id FROM password_resets r
        JOIN users u ON u.id = r.user_id
        WHERE u.email=? AND r.token_hash=? AND r.used_at IS NULL AND r.expires_at > ?
        """,
        (email.strip().lower(), _token_hash(code.strip()), store.now_iso()),
    )
    if not rows:
        raise AppError("重置码无效或已过期")
    user_id = rows[0]["user_id"]
    digest = rows[0]["token_hash"]

    def run(conn) -> None:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (_hash_password(checked), user_id),
        )
        conn.execute(
            "UPDATE password_resets SET used_at=? WHERE token_hash=?",
            (store.now_iso(), digest),
        )
        conn.execute(
            "UPDATE sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
            (store.now_iso(), user_id),
        )

    store.transaction(run)
