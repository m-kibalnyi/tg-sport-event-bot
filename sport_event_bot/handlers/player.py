# -*- coding: utf-8 -*-
from loguru import logger

import sport_event_bot.db_postgres as db
from sport_event_bot.handlers.event_mgmt import show_info
from sport_event_bot.utils.localization import make_translatable_user_id_context
from sport_event_bot.utils.logging_service import log_event


@logger.catch
@make_translatable_user_id_context
async def add_player(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    translate = context.user_data["translate"]
    if db.is_user_penalized(chat_id, user_id):
        await update.message.reply_text(translate("Access denied: you have an active penalty."))
        return
    db.add_or_update_user(
        user_id, update.effective_user.first_name, update.effective_user.last_name, update.effective_user.username
    )
    db.apply_for_participation_in_the_event(chat_id, user_id)
    event_id = db.get_event_id_by_chat_id(chat_id)
    if event_id:
        await log_event(chat_id, event_id, f"User {update.effective_user.first_name} applied via /add", context)
    await show_info(update, context)


@logger.catch
@make_translatable_user_id_context
async def remove_player(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    db.revoke_application_for_the_event(chat_id, user_id)
    event_id = db.get_event_id_by_chat_id(chat_id)
    if event_id:
        await log_event(
            chat_id, event_id, f"User {update.effective_user.first_name} removed application via /remove", context
        )
    await show_info(update, context)


@logger.catch
@make_translatable_user_id_context
async def confirm_payment(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    translate = context.user_data["translate"]
    result = db.process_payment(chat_id, user_id)
    await update.message.reply_text(translate(result["message"]))
    await show_info(update, context)


@logger.catch
@make_translatable_user_id_context
async def add_leg(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    translate = context.user_data["translate"]
    if db.is_user_penalized(chat_id, user_id):
        await update.message.reply_text(translate("Access denied: you have an active penalty."))
        return
    db.apply_for_legioneer(chat_id, user_id)
    event_id = db.get_event_id_by_chat_id(chat_id)
    if event_id:
        await log_event(
            chat_id, event_id, f"User {update.effective_user.first_name} added guest player via command", context
        )
    await show_info(update, context)


@logger.catch
@make_translatable_user_id_context
async def rem_leg(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    db.revoke_for_legioneer(chat_id)
    event_id = db.get_event_id_by_chat_id(chat_id)
    if event_id:
        await log_event(
            chat_id, event_id, f"User {update.effective_user.first_name} removed guest player via command", context
        )
    await show_info(update, context)


async def legioneer_added_message(update, context):
    translate = context.user_data["translate"]
    await update.callback_query.answer(translate("Guest player added"))


async def legioneer_removed_message(update, context):
    translate = context.user_data["translate"]
    await update.callback_query.answer(translate("Guest player removed"))
