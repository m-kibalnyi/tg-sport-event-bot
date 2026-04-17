# -*- coding: utf-8 -*-
import datetime
from typing import List, Tuple, Optional
try:
    from sport_event_bot.db.base import reconnect, _exec, PLATFORM
except (ImportError, ValueError):
    from .base import reconnect, _exec, PLATFORM

def penalty_for_user_in_chat(chat_id: int, user_id: int, operator_id: int, days: int = 14):
    conn = reconnect()
    dtm = datetime.datetime.now()
    expires_at = dtm + datetime.timedelta(days=days)
    _exec(conn, '''
        INSERT INTO Penalties (chat_id, platform, user_id, operation_datetime, operator_id, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s);
    ''', (chat_id, PLATFORM, user_id, dtm, operator_id, expires_at))
    conn.close()

def get_chat_user_rp(chat_id: int) -> List[Tuple[str, int]]:
    conn = reconnect()
    cur = _exec(conn, '''
        SELECT COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, ''), COUNT(p.user_id)
        FROM Penalties p
        JOIN Users u ON p.user_id = u.user_id AND p.platform = u.platform
        WHERE p.chat_id = %s AND p.platform = %s
        GROUP BY u.user_id, u.first_name, u.last_name
        ORDER BY COUNT(p.user_id) DESC;
    ''', (chat_id, PLATFORM))
    rows = cur.fetchall()
    conn.close()
    return [(str(r[0]).strip(), int(r[1])) for r in rows] if rows else []

def get_active_penalties(chat_id: int) -> List[Tuple[str, str]]:
    conn = reconnect()
    now = datetime.datetime.now()
    cur = _exec(conn, '''
        SELECT COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, ''), p.expires_at
        FROM Penalties p
        JOIN Users u ON p.user_id = u.user_id AND p.platform = u.platform
        WHERE p.chat_id = %s AND p.platform = %s AND (p.expires_at IS NULL OR p.expires_at > %s)
        ORDER BY p.expires_at ASC;
    ''', (chat_id, PLATFORM, now))
    rows = cur.fetchall()
    conn.close()
    res = []
    for name, expr in rows:
        if expr:
            diff = expr - now
            expr_str = f"{diff.days}d" if diff.days > 0 else f"{diff.seconds // 3600}h"
        else: expr_str = "permane"
        res.append((str(name).strip(), expr_str))
    return res

def get_user_cancellation_datetime(chat_id: int, user_id: int) -> Optional[datetime.datetime]:
    conn = reconnect()
    cur = _exec(conn, '''
        SELECT operation_datetime FROM Revoked
        WHERE user_id = %s AND event_id = (
            SELECT event_id FROM Events WHERE chat_id = %s AND platform = %s ORDER BY event_id DESC LIMIT 1
        );
    ''', (user_id, chat_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
