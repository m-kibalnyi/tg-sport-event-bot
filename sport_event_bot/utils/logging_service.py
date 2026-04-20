# -*- coding: utf-8 -*-
from loguru import logger

import sport_event_bot.db_postgres as db


async def log_event(chat_id: int, event_id: int, message: str, context):
    """Logs an event and notifies the log topic if configured."""
    db.add_event_log(event_id, message)

    log_thread_id = db.get_log_thread_id(chat_id)
    if log_thread_id:
        try:
            await context.bot.send_message(chat_id=chat_id, message_thread_id=log_thread_id, text=f"📝 {message}")
        except Exception as e:
            logger.warning(f"Failed to send log to topic {log_thread_id}: {e}")
