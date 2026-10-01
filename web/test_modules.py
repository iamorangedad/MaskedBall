"""Module boundaries: accounts, privacy, blocks, and the quota gate."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import http.client
from pathlib import Path

_fd, _db = tempfile.mkstemp(suffix=".sqlite")
os.close(_fd)
os.environ["MASKEDBALL_DB"] = _db
os.environ.pop("MASKEDBALL_SMTP_HOST", None)

from maskedball import accounts, chat, conversations, model, moderation, portraits, space, store
from maskedball.errors import AppError
from maskedball.http import Handler, Server


def _raises(fn):
    try:
        fn()
    except AppError as error:
        return error
    raise AssertionError("expected AppError")


class Modules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store.init()
        store.seed()
        cls.httpd = Server(("127.0.0.1", 0), Handler, None)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        Path(_db).unlink(missing_ok=True)
        Path(_db + "-wal").unlink(missing_ok=True)
        Path(_db + "-shm").unlink(missing_ok=True)

    def request(self, method, path, body=None, cookie=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        raw = json.dumps(body).encode() if body is not None else None
        connection.request(method, path, body=raw, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        data = json.loads(payload.decode() or "{}")
        cookies = response.headers.get_all("Set-Cookie") or []
        connection.close()
        return response.status, data, cookies

    def test_register_login_and_anonymous_space(self):
        status, data, _cookies = self.request("GET", "/api/space")
        self.assertEqual(status, 401)

        status, data, cookies = self.request(
            "POST",
            "/api/register",
            {"email": "ada@example.com", "name": "阿达", "password": "correct-horse"},
        )
        self.assertEqual(status, 200)
        session = next(item for item in cookies if item.startswith("mb_session="))
        self.assertNotIn("ada@example.com", session)
        token = session.split(";", 1)[0]
        status, space_data, _cookies = self.request("GET", "/api/space", cookie=token)
        self.assertEqual(status, 200)
        self.assertEqual(space_data["me"]["name"], "阿达")
        self.assertTrue(space_data["me"]["bio"] == "")

        status, data, _cookies = self.request(
            "POST",
            "/api/login",
            {"email": "ada@example.com", "password": "wrong-password"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(data["error"], "邮箱或密码不对")
        status, missing, _cookies = self.request(
            "POST",
            "/api/login",
            {"email": "missing@example.com", "password": "wrong-password"},
        )
        self.assertEqual(missing["error"], data["error"])

        short = _raises(lambda: accounts.register("short@example.com", "短", "1234567"))
        self.assertEqual(short.status, 400)
        duplicate = _raises(lambda: accounts.register("ada@example.com", "另一个", "correct-horse"))
        self.assertIn("已经注册", str(duplicate))

        status, _data, cleared = self.request("POST", "/api/logout", cookie=token)
        self.assertEqual(status, 200)
        self.assertTrue(any("Max-Age=0" in item for item in cleared))
        status, _data, _cookies = self.request("GET", "/api/space", cookie=token)
        self.assertEqual(status, 401)

    def test_read_body_does_not_stick_to_the_next_send(self):
        _status, data, cookies = self.request(
            "POST",
            "/api/register",
            {"email": "keep-ada@example.com", "name": "连发甲", "password": "correct-horse"},
        )
        token = next(item for item in cookies if item.startswith("mb_session=")).split(";", 1)[0]
        bo = accounts.register("keep-bo@example.com", "连发乙", "correct-horse")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json", "Cookie": token}
        connection.request(
            "POST",
            f"/api/chat/{bo['id']}",
            body=json.dumps({"via": "human", "content": "第一条"}).encode(),
            headers=headers,
        )
        first = connection.getresponse()
        first.read()
        self.assertEqual(first.status, 200)
        connection.request("POST", f"/api/chat/{bo['id']}/read", body=b"{}", headers=headers)
        read_response = connection.getresponse()
        read_response.read()
        self.assertEqual(read_response.status, 200)
        connection.request(
            "POST",
            f"/api/chat/{bo['id']}",
            body=json.dumps({"via": "human", "content": "第二条"}).encode(),
            headers=headers,
        )
        sent = connection.getresponse()
        payload = json.loads(sent.read().decode())
        self.assertEqual(sent.status, 200, payload)
        self.assertEqual([item["content"] for item in payload["messages"]], ["第一条", "第二条"])
        connection.request("GET", "/api/space", headers={"Cookie": token})
        space_response = connection.getresponse()
        space_response.read()
        connection.close()
        self.assertEqual(space_response.status, 200)
        self.assertEqual(data["me"]["name"], "连发甲")

    def test_private_bio_stays_out_of_cards_and_prompts(self):
        ada = accounts.register("bio-ada@example.com", "阿达二", "correct-horse")
        bo = accounts.register("bio-bo@example.com", "阿波", "correct-horse")
        portraits.update(ada["id"], {"bio": "只有阿达自己知道的夜班记录"})
        portraits.update(bo["id"], {"bio": "阿波的私密戏园钥匙"})
        seen = space.snapshot(store.fetch_user(bo["id"]))
        others = [user for user in seen["users"] if user["id"] != bo["id"]]
        blob = json.dumps(others, ensure_ascii=False)
        self.assertNotIn("夜班记录", blob)
        self.assertNotIn("bio", blob)
        prompt = model.build_prompt(
            portraits.prompt_context(store.fetch_user(ada["id"])),
            portraits.prompt_counterpart(store.fetch_user(bo["id"])),
            [],
            "",
        )
        self.assertIn("夜班记录", prompt)
        self.assertNotIn("戏园钥匙", prompt)

    def test_threads_blocks_and_reports(self):
        ada = accounts.register("chat-ada@example.com", "聊天甲", "correct-horse")
        bo = accounts.register("chat-bo@example.com", "聊天乙", "correct-horse")
        ce = accounts.register("chat-ce@example.com", "聊天丙", "correct-horse")
        chat.post(ada, bo["id"], "human", "只有甲乙看得到的句子")
        leaked = conversations.list_messages(ce["id"], ada["id"])
        self.assertFalse(any("只有甲乙" in item["content"] for item in leaked))

        edges = conversations.edges_for(ada["id"])
        self.assertTrue(any({item["a"], item["b"]} == {"seed-linwan", "seed-sucheng"} for item in edges))
        with_linwan = conversations.list_messages(ada["id"], "seed-linwan")
        self.assertEqual(with_linwan, [])

        portraits.update(ce["id"], {"assistMode": "llm"})
        started = threading.Event()
        release = threading.Event()
        original = model.submit

        def slow_reply(*_args, **_kwargs):
            started.set()
            release.wait(3)
            return "晚一点再回"

        model.submit = slow_reply
        try:
            first = chat.post(ada, ce["id"], "human", "第一句")
            self.assertTrue(started.wait(2))
            self.assertEqual([item["content"] for item in first["messages"]], ["第一句"])
            second = chat.post(ada, ce["id"], "human", "不等回复的第二句")
            self.assertEqual(
                [item["content"] for item in second["messages"]],
                ["第一句", "不等回复的第二句"],
            )
        finally:
            release.set()
            time.sleep(0.5)
            model.submit = original

        moderation.block(ada["id"], bo["id"])
        denied = _raises(lambda: chat.post(bo, ada["id"], "human", "还想说一句"))
        self.assertEqual(denied.status, 403)
        denied_back = _raises(lambda: chat.post(ada, bo["id"], "human", "我也不发了"))
        self.assertEqual(denied_back.status, 403)
        hidden = {user["id"] for user in space.snapshot(ada)["users"]}
        self.assertNotIn(bo["id"], hidden)
        still_visible = {user["id"] for user in space.snapshot(bo)["users"]}
        self.assertIn(ada["id"], still_visible)

        moderation.report(ce["id"], ada["id"], "这条是测试报告")
        rows = store.query("SELECT reason FROM reports WHERE reporter_id=?", (ce["id"],))
        self.assertEqual(rows[0]["reason"], "这条是测试报告")

    def test_password_change_and_reset(self):
        user = accounts.register("reset@example.com", "重设", "correct-horse")
        old = accounts.create_session(user["id"])
        fresh = accounts.change_password(user["id"], "correct-horse", "another-horse")
        self.assertIsNone(accounts.user_for_token(old))
        self.assertEqual(accounts.user_for_token(fresh)["id"], user["id"])
        self.assertEqual(accounts.request_reset("nobody@example.com"), "operator")
        self.assertEqual(accounts.request_reset("reset@example.com"), "operator")
        code = accounts.issue_reset("reset@example.com")
        accounts.reset_password("reset@example.com", code, "third-horse1")
        self.assertIsNone(accounts.user_for_token(fresh))
        logged = accounts.authenticate("reset@example.com", "third-horse1")
        self.assertEqual(logged["id"], user["id"])
        wrong = _raises(lambda: accounts.authenticate("reset@example.com", "another-horse"))
        self.assertEqual(wrong.status, 401)

    def test_member_quota(self):
        os.environ["MASKEDBALL_LLM_QUOTA"] = "2"
        model._quota.clear()
        try:
            model.enforce_quota("member-test")
            model.enforce_quota("member-test")
            limited = _raises(lambda: model.enforce_quota("member-test"))
            self.assertEqual(limited.status, 429)
        finally:
            os.environ.pop("MASKEDBALL_LLM_QUOTA", None)
            model._quota.clear()


if __name__ == "__main__":
    unittest.main()
