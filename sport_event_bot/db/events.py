# -*- coding: utf-8 -*-
import datetime
from typing import Optional

try:
    from sport_event_bot.db.base import PLATFORM, _exec, reconnect
    from sport_event_bot.db.chats import register_new_chat_id
except (ImportError, ValueError):
    from .base import PLATFORM, _exec, reconnect
    from .chats import register_new_chat_id


def event(
    chat_id: int,
    description: str,
    dt: datetime.datetime,
    limit: int,
    msg_id: int,
    full_text: str,
    creator_id: int,
    location: str = None,
):
    # Ensure chat is registered (FK constraint)
    register_new_chat_id(chat_id, "ru")
    conn = reconnect()
    dt_str = dt.strftime("%Y-%m-%d %H:%M")
    _exec(
        conn,
        """
        INSERT INTO Events (chat_id, platform, description, datetime, players_limit, latest_bot_message_id, 
                           latest_bot_message_text, status, creator_id, location)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Open', %s, %s);
    """,
        (chat_id, PLATFORM, description, dt_str, limit, str(msg_id), full_text, creator_id, location),
    )
    conn.close()


def update_event_text(chat_id: int, text: str):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET description = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (text, chat_id, PLATFORM),
    )
    conn.close()


def get_event_text(chat_id: int) -> Optional[str]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT description FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_players_limit(chat_id: int, limit: int):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET players_limit = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (limit, chat_id, PLATFORM),
    )
    conn.close()


def get_event_limit(chat_id: int) -> int:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT players_limit FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row and row[0] else 0


def set_event_datetime(chat_id: int, dt_str: str):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET datetime = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (dt_str, chat_id, PLATFORM),
    )
    conn.close()


def get_event_datetime(chat_id: int) -> str:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT datetime FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""


def get_event_location(chat_id: int) -> Optional[str]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT location FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_event_payment_url(chat_id: int) -> Optional[str]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT payment_url FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_event_payment_url(chat_id: int, url: str):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET payment_url = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (url, chat_id, PLATFORM),
    )
    conn.close()


def get_event_extra1(chat_id: int) -> Optional[str]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT extra1 FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_event_extra1(chat_id: int, val: str):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET extra1 = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (val, chat_id, PLATFORM),
    )
    conn.close()


def get_event_telegraph_url(chat_id: int) -> Optional[str]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT telegraph_url FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_event_telegraph_url(chat_id, url):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET telegraph_url = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (url, chat_id, PLATFORM),
    )
    conn.close()


def get_event_id_by_chat_id(chat_id: int) -> Optional[int]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT event_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else None


def get_event_creator(chat_id: int) -> Optional[int]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT creator_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else None


def fix_event(chat_id: int):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET status = 'Closed' WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (chat_id, PLATFORM),
    )
    conn.close()


def close_all_open_events_for_chat(chat_id: int):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET status = 'Closed' WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (chat_id, PLATFORM),
    )
    conn.close()


def get_event_blik_phone(chat_id: int) -> Optional[str]:
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT blik_phone FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def set_event_blik_phone(chat_id: int, phone: str):
    conn = reconnect()
    _exec(
        conn,
        "UPDATE Events SET blik_phone = %s WHERE status = 'Open' AND chat_id = %s AND platform = %s;",
        (phone, chat_id, PLATFORM),
    )
    conn.close()
