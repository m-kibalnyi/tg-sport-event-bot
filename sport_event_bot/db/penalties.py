# -*- coding: utf-8 -*-
import datetime
from typing import List, Optional, Tuple

try:
    from sport_event_bot.db.base import PLATFORM, _exec, reconnect
except (ImportError, ValueError):
    from .base import PLATFORM, _exec, reconnect


def penalty_for_user_in_chat(chat_id: int, user_id: int, operator_id: int, days: int = 14):
    conn = reconnect()
    dtm = datetime.datetime.now()
    expires_at = dtm + datetime.timedelta(days=days)
    _exec(
        conn,
        """
        INSERT INTO Penalties (chat_id, platform, user_id, operation_datetime, operator_id, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s);
    """,
        (chat_id, PLATFORM, user_id, dtm, operator_id, expires_at),
    )
    conn.close()

    # Automatically move player to "I am not going" if they are in the event
    try:
        from sport_event_bot.db.participants import revoke_application_for_the_event
        revoke_application_for_the_event(chat_id, user_id)
    except ImportError:
        pass


def get_chat_user_rp(chat_id: int) -> List[Tuple[str, int]]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, ''), COUNT(p.user_id)
        FROM Penalties p
        JOIN Users u ON p.user_id = u.user_id AND p.platform = u.platform
        WHERE p.chat_id = %s AND p.platform = %s
        GROUP BY u.user_id, u.first_name, u.last_name
        ORDER BY COUNT(p.user_id) DESC;
    """,
        (chat_id, PLATFORM),
    )
    rows = cur.fetchall()
    conn.close()
    return [(str(r[0]).strip(), int(r[1])) for r in rows] if rows else []


def get_active_penalties(chat_id: int) -> List[Tuple[str, str]]:
    conn = reconnect()
    now = datetime.datetime.now()
    cur = _exec(
        conn,
        """
        SELECT COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, ''), p.expires_at
        FROM Penalties p
        JOIN Users u ON p.user_id = u.user_id AND p.platform = u.platform
        WHERE p.chat_id = %s AND p.platform = %s AND (p.expires_at IS NULL OR p.expires_at > %s)
        ORDER BY p.expires_at ASC;
    """,
        (chat_id, PLATFORM, now),
    )
    rows = cur.fetchall()
    conn.close()
    res = []
    for name, expr in rows:
        if expr:
            diff = expr - now
            expr_str = f"{diff.days}d" if diff.days > 0 else f"{diff.seconds // 3600}h"
        else:
            expr_str = "permane"
        res.append((str(name).strip(), expr_str))
    return res


def get_user_cancellation_datetime(chat_id: int, user_id: int) -> Optional[datetime.datetime]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT operation_datetime FROM Revoked
        WHERE user_id = %s AND event_id = (
            SELECT event_id FROM Events WHERE chat_id = %s AND platform = %s ORDER BY event_id DESC LIMIT 1
        );
    """,
        (user_id, chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def is_user_penalized(chat_id: int, user_id: int) -> bool:
    conn = reconnect()
    now = datetime.datetime.now()
    cur = _exec(
        conn,
        """
        SELECT 1 FROM Penalties
        WHERE chat_id = %s AND user_id = %s AND platform = %s AND (expires_at IS NULL OR expires_at > %s)
        LIMIT 1;
    """,
        (chat_id, user_id, PLATFORM, now),
    )
    row = cur.fetchone()
    conn.close()
    return True if row else False


def remove_user_penalties(chat_id: int, user_id: int):
    conn = reconnect()
    _exec(
        conn,
        """
        DELETE FROM Penalties
        WHERE chat_id = %s AND user_id = %s AND platform = %s;
    """,
        (chat_id, user_id, PLATFORM),
    )
    conn.close()

def get_active_penalties_with_uids(chat_id: int) -> List[Tuple[int, str]]:
    conn = reconnect()
    now = datetime.datetime.now()
    cur = _exec(
        conn,
        """
        SELECT u.user_id, COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')
        FROM Penalties p
        JOIN Users u ON p.user_id = u.user_id AND p.platform = u.platform
        WHERE p.chat_id = %s AND p.platform = %s AND (p.expires_at IS NULL OR p.expires_at > %s)
        ORDER BY p.expires_at ASC;
    """,
        (chat_id, PLATFORM, now),
    )
    rows = cur.fetchall()
    conn.close()
    return [(int(r[0]), str(r[1]).strip() or str(r[0])) for r in rows]
