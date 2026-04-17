# -*- coding: utf-8 -*-
from typing import Optional, Set
try:
    from sport_event_bot.db.base import reconnect, _exec, PLATFORM
except (ImportError, ValueError):
    from .base import reconnect, _exec, PLATFORM

def register_new_chat_id(chat_id: int, lang: str):
    conn = reconnect()
    query = 'INSERT INTO Chats(chat_id, platform, lang) VALUES (%s, %s, %s) ON CONFLICT (chat_id, platform) DO NOTHING;'
    _exec(conn, query, (chat_id, PLATFORM, lang or ''))
    conn.close()

def get_all_chat_ids() -> Set[int]:
    conn = reconnect()
    cur = _exec(conn, 'SELECT chat_id FROM Chats WHERE platform = %s;', (PLATFORM,))
    rows = cur.fetchall()
    conn.close()
    return set(int(row[0]) for row in rows)

def get_chat_lang(chat_id: int) -> str:
    conn = reconnect()
    cur = _exec(conn, 'SELECT lang FROM Chats WHERE chat_id = %s AND platform = %s;', (chat_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] else 'en'

def set_chat_lang(chat_id: int, lang: str):
    conn = reconnect()
    _exec(conn, 'UPDATE Chats SET lang = %s WHERE chat_id = %s AND platform = %s;', (lang, chat_id, PLATFORM))
    conn.close()

def get_latest_bot_message_id(chat_id) -> int:
    conn = reconnect()
    cur = _exec(conn, 'SELECT latest_bot_message_id FROM Chats WHERE chat_id = %s AND platform = %s LIMIT 1;', (chat_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    if row and row[0]:
        try: return int(row[0])
        except (ValueError, TypeError): return 0
    return 0

def get_latest_bot_message_text(chat_id) -> str:
    conn = reconnect()
    cur = _exec(conn, 'SELECT latest_bot_message_text FROM Chats WHERE chat_id = %s AND platform = %s LIMIT 1;', (chat_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else ""

def save_latest_bot_message(chat_id, message_id, message_text):
    conn = reconnect()
    _exec(conn, 'UPDATE Chats SET latest_bot_message_id = %s, latest_bot_message_text = %s WHERE chat_id = %s AND platform = %s;',
          (str(message_id), message_text, chat_id, PLATFORM))
    conn.close()

def get_log_thread_id(chat_id: int) -> Optional[int]:
    conn = reconnect()
    cur = _exec(conn, 'SELECT log_thread_id FROM Chats WHERE chat_id = %s AND platform = %s;', (chat_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else None

def set_log_thread_id(chat_id: int, thread_id: Optional[int]):
    conn = reconnect()
    _exec(conn, 'UPDATE Chats SET log_thread_id = %s WHERE chat_id = %s AND platform = %s;', (thread_id, chat_id, PLATFORM))
    conn.close()

def get_lists_thread_id(chat_id: int) -> Optional[int]:
    conn = reconnect()
    cur = _exec(conn, 'SELECT lists_thread_id FROM Chats WHERE chat_id = %s AND platform = %s;', (chat_id, PLATFORM))
    row = cur.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else None

def set_lists_thread_id(chat_id: int, thread_id: Optional[int]):
    conn = reconnect()
    _exec(conn, 'UPDATE Chats SET lists_thread_id = %s WHERE chat_id = %s AND platform = %s;', (thread_id, chat_id, PLATFORM))
    conn.close()
