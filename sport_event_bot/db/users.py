# -*- coding: utf-8 -*-
from typing import List

try:
    from sport_event_bot.db.base import PLATFORM, _exec, reconnect
except (ImportError, ValueError):
    from .base import PLATFORM, _exec, reconnect


def add_or_update_user(user_id, first_name="", last_name="", username=""):
    conn = reconnect()
    query = """
        INSERT INTO Users (user_id, platform, first_name, last_name, username)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, platform)
        DO UPDATE SET first_name = EXCLUDED.first_name, last_name = EXCLUDED.last_name, username = EXCLUDED.username;
    """
    _exec(conn, query, (user_id, PLATFORM, first_name or "", last_name or "", username or ""))
    conn.close()


def compose_full_name(user_id: int) -> str:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT first_name, last_name, username FROM Users WHERE user_id = %s AND platform = %s;",
        (user_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return str(user_id)
    fnm, lnm, unm = (row[0] or ""), (row[1] or ""), (row[2] or "")
    res = " ".join([fnm, lnm]).strip()
    if res and unm:
        res = f"{res} ({unm})"
    return res or unm or str(user_id)


def get_all_userids() -> List[int]:
    conn = reconnect()
    cur = _exec(conn, "SELECT user_id FROM Users WHERE platform = %s;", (PLATFORM,))
    rows = cur.fetchall()
    conn.close()
    return [int(row[0]) for row in rows]


def get_user_lang(user_id: int) -> str:
    conn = reconnect()
    cur = _exec(conn, "SELECT lang FROM Users WHERE user_id = %s AND platform = %s;", (user_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else "ru"


def set_user_lang(user_id: int, lang: str):
    conn = reconnect()
    _exec(conn, "UPDATE Users SET lang = %s WHERE user_id = %s AND platform = %s;", (lang, user_id, PLATFORM))
    conn.close()
