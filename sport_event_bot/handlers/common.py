# -*- coding: utf-8 -*-
from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from sport_event_bot.utils.localization import make_translatable_user_id_context


@logger.catch
@make_translatable_user_id_context
async def set_language(update, context):
    if not update.message:
        return
    translate = context.user_data["translate"]
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="SET_LANG_ru")],
        [InlineKeyboardButton("Українська", callback_data="SET_LANG_uk")],
        [InlineKeyboardButton("Polski", callback_data="SET_LANG_pl")],
        [InlineKeyboardButton("English", callback_data="SET_LANG_en")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(translate("Choose your language:"), reply_markup=reply_markup)


@logger.catch
@make_translatable_user_id_context
async def show_help(update, context):
    if not update.message:
        return
    translate = context.user_data["translate"]
    help_text = translate("""
Available BOT commands:

/event TEXT - Register new event (or /event {name: "...", limit: 10} for one-shot)
/event_remove - Remove open event
/event_update TEXT - Change event description
/limit XX - Set players limit
/event_datetime DATE TIME - Set event date/time
/info - Show event details
/add - Register yourself
/remove - Revoke application
/add_leg - Register guest
/rem_leg - Revoke guest
/pay - Confirm payment
/payments - Show payment log
/blik PHONE - Set BLIK phone
/lang - Change language
/fix - Refresh event view
/penalty USER - Give yellow card
/penalty_remove USER - Remove yellow card
/stat - Group statistics
/set_lists_topic - Set this thread for event lists
/set_logs_topic - Set this thread for logs
""")
    await update.message.reply_text(help_text)


@make_translatable_user_id_context
async def start(update, context):
    translate = context.user_data["translate"]
    await update.message.reply_text(translate("Welcome! Use /help to see available commands."))
