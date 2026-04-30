# -*- coding: utf-8 -*-
import datetime
from typing import List, Tuple

try:
    from sport_event_bot.db.base import PLATFORM, _exec, reconnect
except (ImportError, ValueError):
    from .base import PLATFORM, _exec, reconnect


def get_event_users(chat_id: int) -> List[Tuple[int, int]]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT p.user_id, p.invited_by
        FROM Participants p
        WHERE p.event_id = (SELECT e.event_id FROM Events e WHERE e.status = 'Open' AND e.chat_id = %s AND e.platform = %s LIMIT 1)
        ORDER BY p.operation_datetime;
    """,
        (chat_id, PLATFORM),
    )
    rows = cur.fetchall()
    conn.close()
    return [(int(r[0]), r[1] if r[1] is None else int(r[1])) for r in rows] if rows else []


def get_event_revoked_users(chat_id: int) -> List[int]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT r.user_id
        FROM Revoked r
        WHERE r.event_id = (SELECT e.event_id FROM Events e WHERE e.status = 'Open' AND e.chat_id = %s AND e.platform = %s LIMIT 1)
        ORDER BY r.operation_datetime;
    """,
        (chat_id, PLATFORM),
    )
    rows = cur.fetchall()
    conn.close()
    return [int(r[0]) for r in rows] if rows else []


def get_thinking_users(chat_id: int) -> List[int]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT t.user_id
        FROM Thinking t
        WHERE t.event_id = (SELECT e.event_id FROM Events e WHERE e.status = 'Open' AND e.chat_id = %s AND e.platform = %s LIMIT 1)
        ORDER BY t.operation_datetime;
    """,
        (chat_id, PLATFORM),
    )
    rows = cur.fetchall()
    conn.close()
    return [int(r[0]) for r in rows] if rows else []


def apply_for_participation_in_the_event(chat_id: int, user_id: int):
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT event_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    event = cur.fetchone()
    if not event:
        conn.close()
        return
    event_id = event[0]
    dtm = datetime.datetime.now()
    _exec(
        conn,
        """
        INSERT INTO Participants (event_id, user_id, operation_datetime, paid)
        VALUES (%s, %s, %s, FALSE)
        ON CONFLICT (event_id, user_id) DO NOTHING;
    """,
        (event_id, user_id, dtm),
    )
    _exec(conn, "DELETE FROM Revoked WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    _exec(conn, "DELETE FROM Thinking WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    conn.close()


def revoke_application_for_the_event(chat_id: int, user_id: int):
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT event_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    event = cur.fetchone()
    if not event:
        conn.close()
        return
    event_id = event[0]
    dtm = datetime.datetime.now()
    _exec(
        conn,
        """
        INSERT INTO Revoked (event_id, user_id, operation_datetime)
        VALUES (%s, %s, %s)
        ON CONFLICT (event_id, user_id) DO NOTHING;
    """,
        (event_id, user_id, dtm),
    )
    _exec(conn, "DELETE FROM Participants WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    _exec(conn, "DELETE FROM Thinking WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    conn.close()


def apply_for_thinking(chat_id: int, user_id: int):
    conn = reconnect()
    cur = _exec(
        conn,
        "SELECT event_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1;",
        (chat_id, PLATFORM),
    )
    event = cur.fetchone()
    if not event:
        conn.close()
        return
    event_id = event[0]
    dtm = datetime.datetime.now()
    _exec(
        conn,
        """
        INSERT INTO Thinking (event_id, user_id, operation_datetime)
        VALUES (%s, %s, %s)
        ON CONFLICT (event_id, user_id) DO NOTHING;
    """,
        (event_id, user_id, dtm),
    )
    _exec(conn, "DELETE FROM Participants WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    _exec(conn, "DELETE FROM Revoked WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    conn.close()


def get_legioneer_user(event_id: int):
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT MAX(user_id) FROM (
            SELECT user_id FROM Participants WHERE event_id = %s AND user_id >= 10 AND user_id < 1010
            UNION ALL
            SELECT user_id FROM Thinking WHERE event_id = %s AND user_id >= 10 AND user_id < 1010
            UNION ALL
            SELECT user_id FROM Revoked WHERE event_id = %s AND user_id >= 10 AND user_id < 1010
        ) as all_legs;
        """,
        (event_id, event_id, event_id),
    )
    res = cur.fetchone()
    conn.close()
    if res and res[0]:
        return int(res[0]) + 1
    return 10


def apply_for_legioneer(chat_id, invited_by_user_id=None):
    from sport_event_bot.db.events import get_event_id_by_chat_id

    conn = reconnect()
    event_id = get_event_id_by_chat_id(chat_id)
    if not event_id:
        conn.close()
        return
    user_id = get_legioneer_user(event_id)
    dtm = datetime.datetime.now()
    _exec(
        conn,
        """
        INSERT INTO Participants (event_id, user_id, operation_datetime, paid, invited_by)
        VALUES (%s, %s, %s, FALSE, %s)
        ON CONFLICT (event_id, user_id) DO NOTHING;
    """,
        (event_id, user_id, dtm, invited_by_user_id),
    )
    _exec(conn, "DELETE FROM Revoked WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    conn.close()


def revoke_for_legioneer(chat_id):
    from sport_event_bot.db.events import get_event_id_by_chat_id

    conn = reconnect()
    event_id = get_event_id_by_chat_id(chat_id)
    if not event_id:
        conn.close()
        return
    user_id = get_legioneer_user(event_id) - 1
    if user_id > 9:
        _exec(conn, "DELETE FROM Participants WHERE event_id = %s AND user_id = %s;", (event_id, user_id))
    conn.close()


def revoke_all_user_legioneers(chat_id, user_id):
    from sport_event_bot.db.events import get_event_id_by_chat_id

    conn = reconnect()
    event_id = get_event_id_by_chat_id(chat_id)
    if not event_id:
        conn.close()
        return
    _exec(conn, "DELETE FROM Participants WHERE event_id = %s AND invited_by = %s;", (event_id, user_id))
    conn.close()


def get_only_chat_participants(chat_id: int) -> List[int]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT DISTINCT p.user_id
        FROM Participants p
        WHERE p.event_id = (SELECT e.event_id FROM Events e WHERE e.chat_id = %s AND e.platform = %s ORDER BY e.event_id DESC LIMIT 1);
    """,
        (chat_id, PLATFORM),
    )
    rows = cur.fetchall()
    conn.close()
    return [int(r[0]) for r in rows] if rows else []
