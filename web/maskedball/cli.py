"""Process entry: open the database, start the model queue, then serve HTTP."""

from __future__ import annotations

import sys
import threading
import time

from maskedball import accounts, config, model, store
from maskedball.errors import AppError
from maskedball.http import serve


def _backup_loop() -> None:
    while True:
        time.sleep(15 * 60)
        try:
            store.backup_once()
        except Exception as error:
            print(f"[store] 备份失败：{error}", flush=True)


def main() -> None:
    store.init()
    if len(sys.argv) > 1 and sys.argv[1] == "--issue-reset":
        if len(sys.argv) < 3:
            print("用法: python3 web/server.py --issue-reset 邮箱", file=sys.stderr)
            raise SystemExit(2)
        try:
            print(accounts.issue_reset(sys.argv[2]))
        except AppError as error:
            print(str(error), file=sys.stderr)
            raise SystemExit(1) from error
        return
    store.seed()
    try:
        path = store.backup_once()
        print(f"[store] 备份 {path}", flush=True)
    except Exception as error:
        print(f"[store] 备份失败：{error}", flush=True)
    threading.Thread(target=_backup_loop, name="maskedball-backup", daemon=True).start()
    model.start()
    print(f"[store] {config.db_path()}", flush=True)
    serve()
