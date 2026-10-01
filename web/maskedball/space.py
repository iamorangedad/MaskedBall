"""The graph a signed-in person is allowed to see."""

from __future__ import annotations

from maskedball import config, conversations, moderation, portraits, presence, store


def snapshot(viewer: dict) -> dict:
    fresh = store.fetch_user(viewer["id"]) or viewer
    hidden = moderation.ids_blocked_by(fresh["id"])
    users = []
    for user in store.list_users():
        if user["id"] in hidden:
            continue
        current = fresh if user["id"] == fresh["id"] else user
        is_online = presence.online(current)
        unread = 0 if user["id"] == fresh["id"] else conversations.unread(fresh["id"], user["id"])
        if user["id"] == fresh["id"]:
            users.append(
                portraits.private_view(current, is_online, moderation.blocked_people(fresh["id"]))
            )
        else:
            users.append(portraits.public_card(current, is_online, unread))
    me = next(item for item in users if item["id"] == fresh["id"])
    catalog = portraits.catalog()
    catalog["model"] = config.model_name()
    return {
        "me": me,
        "users": users,
        "edges": conversations.edges_for(fresh["id"]),
        "catalog": catalog,
    }
