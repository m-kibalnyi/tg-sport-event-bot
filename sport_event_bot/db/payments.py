# -*- coding: utf-8 -*-
import datetime
from typing import List, Tuple

try:
    from sport_event_bot.db.base import PLATFORM, _exec, reconnect
except (ImportError, ValueError):
    from .base import PLATFORM, _exec, reconnect


def set_payment_status(chat_id: int, user_id: int, paid: bool = True):
    conn = reconnect()
    paid_at = datetime.datetime.now() if paid else None
    _exec(
        conn,
        """
        UPDATE Participants SET paid = %s, paid_at = %s
        WHERE user_id = %s AND event_id = (
            SELECT event_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1
        );
    """,
        (paid, paid_at, user_id, chat_id, PLATFORM),
    )
    conn.close()


def get_payment_status(chat_id: int, user_id: int) -> bool:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT p.paid FROM Participants p
        WHERE p.user_id = %s AND p.event_id = (
            SELECT event_id FROM Events WHERE status = 'Open' AND chat_id = %s AND platform = %s LIMIT 1
        );
    """,
        (user_id, chat_id, PLATFORM),
    )
    row = cur.fetchone()
    conn.close()
    return bool(row[0]) if row else False


def process_payment(chat_id: int, user_id: int) -> dict:
    current_status = get_payment_status(chat_id, user_id)
    new_status = not current_status
    set_payment_status(chat_id, user_id, new_status)
    msg = "Payment confirmed" if new_status else "Payment revoked"
    return {"success": True, "message": msg}


def get_payment_log(chat_id: int) -> List[Tuple[str, datetime.datetime, bool]]:
    conn = reconnect()
    cur = _exec(
        conn,
        """
        SELECT COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, ''), p.paid_at, (p.invited_by IS NOT NULL) as for_friend
        FROM Participants p
        LEFT JOIN Users u ON p.user_id = u.user_id AND u.platform = %s
        WHERE p.event_id = (SELECT e.event_id FROM Events e WHERE e.status = 'Open' AND e.chat_id = %s AND e.platform = %s LIMIT 1)
        AND p.paid = TRUE
        ORDER BY p.paid_at ASC;
    """,
        (PLATFORM, chat_id, PLATFORM),
    )
    rows = cur.fetchall()
    conn.close()
    return [(str(r[0]).strip() or "Unknown", r[1], bool(r[2])) for r in rows] if rows else []
