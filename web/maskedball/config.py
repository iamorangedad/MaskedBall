import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip() in {"1", "true", "yes"}


def host() -> str:
    return os.environ.get("MASKEDBALL_HOST", "127.0.0.1")


def port() -> int:
    return int(os.environ.get("MASKEDBALL_PORT", "8787"))


def db_path() -> Path:
    override = os.environ.get("MASKEDBALL_DB")
    if override:
        return Path(override)
    return ROOT / "data" / "space.sqlite"


def backup_dir() -> Path:
    return db_path().parent / "backups"


def static_dir() -> Path:
    return ROOT / "static"


def model_name() -> str:
    return os.environ.get("MASKEDBALL_MODEL", "qwen3:4b")


def ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")


def llm_timeout() -> float:
    return float(os.environ.get("MASKEDBALL_LLM_TIMEOUT", "45"))


def llm_quota() -> int:
    return int(os.environ.get("MASKEDBALL_LLM_QUOTA", "30"))


def tls_paths() -> tuple[str, str] | None:
    cert = os.environ.get("MASKEDBALL_TLS_CERT", "").strip()
    key = os.environ.get("MASKEDBALL_TLS_KEY", "").strip()
    if cert and key:
        return cert, key
    return None


def secure_cookie() -> bool:
    return tls_paths() is not None or _flag("MASKEDBALL_SECURE_COOKIE")


def smtp() -> dict | None:
    host_name = os.environ.get("MASKEDBALL_SMTP_HOST", "").strip()
    if not host_name:
        return None
    return {
        "host": host_name,
        "port": int(os.environ.get("MASKEDBALL_SMTP_PORT", "587")),
        "user": os.environ.get("MASKEDBALL_SMTP_USER", ""),
        "password": os.environ.get("MASKEDBALL_SMTP_PASSWORD", ""),
        "from": os.environ.get("MASKEDBALL_SMTP_FROM", "maskedball@localhost"),
    }
