# -*- coding: utf-8 -*-
from loguru import logger
from telegram.constants import ParseMode

import sport_event_bot.db_postgres as db
from sport_event_bot.ui.markups import build_message_markup
from sport_event_bot.ui.render import create_event_full_text
from sport_event_bot.utils.localization import make_translatable_user_id_context


@logger.catch
@make_translatable_user_id_context
async def show_info(update, context):
    chat_id = update.effective_chat.id
    translate = context.user_data["translate"]
    full_text = create_event_full_text(chat_id, translate)
    reply_markup = build_message_markup(translate, db.get_event_extra1(chat_id))

    lists_thread_id = db.get_lists_thread_id(chat_id)
    if lists_thread_id is None and update.effective_message and update.effective_message.is_topic_message:
        lists_thread_id = update.effective_message.message_thread_id

    if update.callback_query:
        await update.callback_query.edit_message_text(
            full_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    else:
        msg = await update.message.reply_text(
            full_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            message_thread_id=lists_thread_id,
        )
        db.save_latest_bot_message(chat_id, msg.message_id, full_text)


def parse_cmd_arg(update, context) -> str:
    if context.args:
        return " ".join(context.args)
    return ""
