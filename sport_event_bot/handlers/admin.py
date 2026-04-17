# -*- coding: utf-8 -*-
from loguru import logger
import sport_event_bot.db_postgres as db
import sport_event_bot.telegraph as tph
from sport_event_bot.utils.localization import make_translatable_user_id_context
from sport_event_bot.handlers.event_mgmt import show_info

@logger.catch
@make_translatable_user_id_context
async def set_players_limit(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    try:
        limit = int(context.args[0])
        db.set_players_limit(chat_id, limit)
        await update.message.reply_text(translate("Players limit updated: %(limit)d") % {'limit': limit})
    except:
        await update.message.reply_text(translate("Usage: /limit XX"))

@logger.catch
@make_translatable_user_id_context
async def show_stat(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    stats = db.get_chat_user_rp(chat_id)
    if not stats:
        await update.message.reply_text(translate("No statistics available yet."))
        return
    text = translate("Group statistics:") + "\n"
    for name, count in stats:
        text += f" - {name}: {count}\n"
    await update.message.reply_text(text)

@logger.catch
@make_translatable_user_id_context
async def penalty_player(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    if not context.args:
        await update.message.reply_text(translate("Usage: /penalty USERID [DAYS]"))
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1]) if len(context.args) > 1 else 14
        db.penalty_for_user_in_chat(chat_id, user_id, update.effective_user.id, days)
        await update.message.reply_text(translate("Penalty applied for %(days)d days.") % {'days': days})
    except:
        await update.message.reply_text(translate("Invalid user ID or days."))

@logger.catch
@make_translatable_user_id_context
async def show_payments(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    try:
        entries = db.get_payment_log(chat_id)
        if not entries:
            await update.message.reply_text(translate("No payments recorded yet."))
            return
        event_title = db.get_event_text(chat_id) or 'Event'
        tph_url = await tph.publish_payment_log(event_title, entries, db.get_event_telegraph_url(chat_id))
        db.set_event_telegraph_url(chat_id, tph_url)
        await update.message.reply_text(f"💳 {translate('Payment log')}: {tph_url}")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"Error: {e}")

@logger.catch
@make_translatable_user_id_context
async def fix_ui(update, context):
    if not update.message: return
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def set_lists_topic(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    thread_id = update.message.message_thread_id
    db.set_lists_thread_id(chat_id, thread_id)
    await update.message.reply_text(translate("Lists topic configured for this thread."))

@logger.catch
@make_translatable_user_id_context
async def set_logs_topic(update, context):
    if not update.message: return
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    thread_id = update.message.message_thread_id
    db.set_log_thread_id(chat_id, thread_id)
    await update.message.reply_text(translate("Logs topic configured for this thread."))
