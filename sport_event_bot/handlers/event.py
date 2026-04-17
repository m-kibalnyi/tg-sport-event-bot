# -*- coding: utf-8 -*-
from loguru import logger
import sport_event_bot.db_postgres as db
from sport_event_bot.utils.localization import make_translatable_user_id_context
from sport_event_bot.utils.logging_service import log_event
from sport_event_bot.ui.render import create_event_full_text
from sport_event_bot.ui.markups import build_message_markup
from sport_event_bot.handlers.event_mgmt import show_info

@logger.catch
@make_translatable_user_id_context
async def set_event_datetime(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    if not context.args:
        await update.message.reply_text(translate("Usage: /event_datetime DATE TIME"))
        return
    dt_str = " ".join(context.args)
    db.set_event_datetime(chat_id, dt_str)
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def remove_all_chat_events(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    db.close_all_open_events_for_chat(chat_id)
    await update.message.reply_text(translate("All open events for this chat were closed."))

@logger.catch
@make_translatable_user_id_context
async def set_blik(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    if not context.args:
        await update.message.reply_text(translate("Usage: /blik PHONE"))
        return
    phone = context.args[0]
    db.set_event_blik_phone(chat_id, phone)
    await update.message.reply_text(translate("BLIK phone updated."))

@logger.catch
@make_translatable_user_id_context
async def update_event(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    if not context.args:
        await update.message.reply_text(translate("Usage: /event_update TEXT"))
        return
    new_text = " ".join(context.args)
    db.update_event_text(chat_id, new_text)
    await show_info(update, context)
