# -*- coding: utf-8 -*-
import datetime
from typing import List, Tuple
try:
    from sport_event_bot.db.base import reconnect, _exec, PLATFORM
except (ImportError, ValueError):
    from .base import reconnect, _exec, PLATFORM

def add_event_log(event_id: int, message: str):
    conn = reconnect()
    _exec(conn, 'INSERT INTO EventLogs (event_id, message) VALUES (%s, %s);', (event_id, message))
    conn.close()

def get_event_logs(event_id: int) -> List[Tuple[str, datetime.datetime]]:
    conn = reconnect()
    cur = _exec(conn, 'SELECT message, operation_datetime FROM EventLogs WHERE event_id = %s ORDER BY operation_datetime DESC;', (event_id,))
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows] if rows else []

def prune_old_event_logs(days: int = 30):
    conn = reconnect()
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    _exec(conn, 'DELETE FROM EventLogs WHERE operation_datetime < %s;', (cutoff,))
    conn.close()
