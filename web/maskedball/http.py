"""HTTP adapter: routes, cookies, static files, and the event stream."""

from __future__ import annotations

import json
import queue
import ssl
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from maskedball import accounts, chat, config, conversations, moderation, model, notify, portraits, presence, space, store
from maskedball.errors import AppError


def session_cookies(token: str | None = None) -> list[str]:
    secure = "; Secure" if config.secure_cookie() else ""
    clear_legacy = "mb_id=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
    if not token:
        return [
            "mb_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
            clear_legacy,
        ]
    max_age = 30 * 24 * 3600
    return [
        f"mb_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{secure}",
        clear_legacy,
    ]


class Handler(BaseHTTPRequestHandler):
    server_version = "MaskedBall/2.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[http] {self.address_string()} {fmt % args}", flush=True)

    def send_json(self, payload: dict, status: int = 200, cookies: list[str] | None = None) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 100_000:
            raise AppError("请求太大")
        if length == 0:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode())
        except json.JSONDecodeError as error:
            raise AppError("请求格式不对") from error
        if not isinstance(data, dict):
            raise AppError("请求格式不对")
        return data

    def token(self) -> str | None:
        jar = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = jar.get("mb_session")
        if morsel is None or not morsel.value:
            return None
        return morsel.value

    def viewer(self, required: bool = True) -> dict | None:
        user = accounts.user_for_token(self.token())
        if user is None and required:
            raise AppError("请先登录", 401)
        if user is not None:
            presence.touch(user["id"])
        return user

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/space":
                self.handle_space()
                return
            if path == "/api/events":
                self.handle_events()
                return
            if path == "/api/health":
                self.send_json(model.health())
                return
            if path.startswith("/api/chat/") and path.endswith("/read"):
                self.send_json({"error": "没有这个接口"}, 404)
                return
            if path.startswith("/api/chat/"):
                self.handle_get_chat(unquote(path[len("/api/chat/") :]))
                return
            self.handle_static(path)
        except AppError as error:
            self.send_json({"error": str(error)}, error.status)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/register":
                self.handle_register()
                return
            if path == "/api/login":
                self.handle_login()
                return
            if path == "/api/logout":
                self.handle_logout()
                return
            if path == "/api/password/forgot":
                self.handle_forgot()
                return
            if path == "/api/password/reset":
                self.handle_reset()
                return
            if path == "/api/password/change":
                self.handle_change_password()
                return
            if path == "/api/reports":
                self.handle_report()
                return
            if path == "/api/blocks":
                self.handle_block()
                return
            if path.startswith("/api/chat/") and path.endswith("/read"):
                other_id = unquote(path[len("/api/chat/") : -len("/read")])
                self.handle_read(other_id)
                return
            if path.startswith("/api/chat/"):
                self.handle_post_chat(unquote(path[len("/api/chat/") :]))
                return
            self.send_json({"error": "没有这个接口"}, 404)
        except AppError as error:
            self.send_json({"error": str(error)}, error.status)

    def do_PUT(self) -> None:
        try:
            if urlparse(self.path).path == "/api/me":
                user = self.viewer()
                portraits.update(user["id"], self.read_json())
                self.send_json(space.snapshot(user))
                return
            self.send_json({"error": "没有这个接口"}, 404)
        except AppError as error:
            self.send_json({"error": str(error)}, error.status)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/blocks/"):
                user = self.viewer()
                moderation.unblock(user["id"], unquote(path[len("/api/blocks/") :]))
                self.send_json(space.snapshot(user))
                return
            self.send_json({"error": "没有这个接口"}, 404)
        except AppError as error:
            self.send_json({"error": str(error)}, error.status)

    def handle_register(self) -> None:
        body = self.read_json()
        user = accounts.register(
            str(body.get("email", "")),
            str(body.get("name", "")),
            str(body.get("password", "")),
        )
        token = accounts.create_session(user["id"])
        presence.touch(user["id"])
        self.send_json(space.snapshot(user), cookies=session_cookies(token))

    def handle_login(self) -> None:
        body = self.read_json()
        user = accounts.authenticate(str(body.get("email", "")), str(body.get("password", "")))
        token = accounts.create_session(user["id"])
        presence.touch(user["id"])
        self.send_json(space.snapshot(user), cookies=session_cookies(token))

    def handle_logout(self) -> None:
        accounts.revoke_token(self.token() or "")
        self.send_json({"ok": True}, cookies=session_cookies(None))

    def handle_forgot(self) -> None:
        body = self.read_json()
        delivery = accounts.request_reset(str(body.get("email", "")))
        self.send_json({"ok": True, "delivery": delivery})

    def handle_reset(self) -> None:
        body = self.read_json()
        accounts.reset_password(
            str(body.get("email", "")),
            str(body.get("code", "")),
            str(body.get("password", "")),
        )
        self.send_json({"ok": True})

    def handle_change_password(self) -> None:
        user = self.viewer()
        body = self.read_json()
        token = accounts.change_password(
            user["id"],
            str(body.get("current", "")),
            str(body.get("password", "")),
        )
        self.send_json({"ok": True}, cookies=session_cookies(token))

    def handle_report(self) -> None:
        user = self.viewer()
        body = self.read_json()
        moderation.report(user["id"], str(body.get("targetId", "")), str(body.get("reason", "")))
        self.send_json({"ok": True})

    def handle_block(self) -> None:
        user = self.viewer()
        body = self.read_json()
        moderation.block(user["id"], str(body.get("targetId", "")))
        self.send_json(space.snapshot(user))

    def handle_space(self) -> None:
        self.send_json(space.snapshot(self.viewer()))

    def handle_get_chat(self, other_id: str) -> None:
        user = self.viewer()
        if moderation.is_blocked(user["id"], other_id):
            raise AppError("你们之间现在不能发消息", 403)
        conversations.mark_read(user["id"], other_id)
        other = store.fetch_user(other_id)
        self.send_json(
            {
                "messages": conversations.list_messages(user["id"], other_id),
                "other": portraits.public_card(other, presence.online(other)) if other else None,
            }
        )

    def handle_read(self, other_id: str) -> None:
        user = self.viewer()
        conversations.mark_read(user["id"], other_id)
        self.send_json({"ok": True, "edge": conversations.edge_between(user["id"], other_id)})

    def handle_post_chat(self, other_id: str) -> None:
        user = self.viewer()
        body = self.read_json()
        self.send_json(
            chat.post(
                user,
                other_id,
                str(body.get("via", "human")),
                str(body.get("content", "")),
            )
        )

    def handle_events(self) -> None:
        user = self.viewer()
        mailbox = notify.subscribe(user["id"])
        presence.touch(user["id"])
        notify.broadcast("presence", {"id": user["id"], "online": True})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.connection.settimeout(30)
        try:
            while True:
                try:
                    event, data = mailbox.get(timeout=15)
                except queue.Empty:
                    presence.touch(user["id"])
                    event, data = "ping", {}
                    notify.broadcast("presence", {"id": user["id"], "online": True})
                payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                self.wfile.write(payload.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            return
        finally:
            notify.unsubscribe(user["id"], mailbox)

    def handle_static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        root = config.static_dir().resolve()
        target = (root / path.lstrip("/")).resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
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
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(raw)


class Server(ThreadingHTTPServer):
    def __init__(self, address, handler, tls: tuple[str, str] | None):
        super().__init__(address, handler)
        if tls:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(tls[0], tls[1])
            self.socket = context.wrap_socket(self.socket, server_side=True)


def serve() -> None:
    tls = config.tls_paths()
    server = Server((config.host(), config.port()), Handler, tls)
    scheme = "https" if tls else "http"
    print(f"MaskedBall web  {scheme}://{config.host()}:{config.port()}", flush=True)
    print(f"模型  {config.model_name()}  via  {config.ollama_url()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止", flush=True)
    finally:
        server.server_close()
