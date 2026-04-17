# -*- coding: utf-8 -*-
from loguru import logger
import sport_event_bot.db_postgres as db
from sport_event_bot.utils.localization import make_translatable_user_id_context
from sport_event_bot.handlers.event_mgmt import show_info

async def forum_topic_created_handler(update, context):
    """Automatically detect 'Logs' and 'Lists' topics on creation"""
    if not update.message or not update.message.forum_topic_created: return
    name = update.message.forum_topic_created.name.lower().strip()
    chat_id = update.message.chat_id
    thread_id = update.message.message_thread_id
    log_names = ['logs', 'журнал', 'логи', 'log', 'журнал\логи', 'notification', 'notifications']
    list_names = ['списки', 'lists', 'events', 'события', 'список', 'list', 'event']
    if any(n in name for n in log_names):
        db.set_log_thread_id(chat_id, thread_id)
        logger.info(f"Set log topic for chat {chat_id}: {name} ({thread_id})")
    elif any(n in name for n in list_names):
        db.set_lists_thread_id(chat_id, thread_id)
        logger.info(f"Set lists topic for chat {chat_id}: {name} ({thread_id})")

@logger.catch
@make_translatable_user_id_context
async def unknown_command_handler(update, context):
    if not update.message: return
    if update.message.new_chat_members: await show_info(update, context)
    text = (update.message.text or "").strip()
    if text.startswith('/'): logger.info(f'Unknown command: {text}')
