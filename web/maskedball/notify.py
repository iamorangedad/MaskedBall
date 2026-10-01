"""In-memory fan-out for people who currently hold an event stream. Nothing is stored."""

from __future__ import annotations

import queue
import threading

_lock = threading.Lock()
_subscribers: dict[str, list[queue.Queue]] = {}


def subscribe(user_id: str) -> queue.Queue:
    mailbox: queue.Queue = queue.Queue()
    with _lock:
        _subscribers.setdefault(user_id, []).append(mailbox)
    return mailbox


def unsubscribe(user_id: str, mailbox: queue.Queue) -> None:
    with _lock:
        mailboxes = _subscribers.get(user_id, [])
        if mailbox in mailboxes:
            mailboxes.remove(mailbox)
        if not mailboxes:
            _subscribers.pop(user_id, None)


def publish(user_id: str, event: str, data: dict) -> None:
    with _lock:
        mailboxes = list(_subscribers.get(user_id, []))
    for mailbox in mailboxes:
        mailbox.put((event, data))


def broadcast(event: str, data: dict) -> None:
    with _lock:
        mailboxes = [mailbox for group in _subscribers.values() for mailbox in group]
    for mailbox in mailboxes:
        mailbox.put((event, data))
