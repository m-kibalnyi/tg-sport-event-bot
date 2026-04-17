# -*- coding: utf-8 -*-
from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ConversationHandler
from telegram.constants import ParseMode
import sport_event_bot.db_postgres as db
from sport_event_bot.utils.localization import make_translatable_user_id_context
from sport_event_bot.utils.helpers import get_default_datetime, parse_loose_json, parse_datetime
from sport_event_bot.utils.logging_service import log_event
from sport_event_bot.ui.render import create_event_full_text, LOCATION_HIDE_MARKER
from sport_event_bot.ui.markups import build_message_markup
from sport_event_bot.handlers.event_mgmt import parse_cmd_arg

EVENT_SET_NAME, EVENT_SET_LIMIT, EVENT_SET_DATETIME, EVENT_SET_PAYMENT, EVENT_SET_BLIK = range(5)

@logger.catch
@make_translatable_user_id_context
async def create_new_event(update, context):
    if not update.message: return ConversationHandler.END
    chat_id = update.message.chat_id
    translate = context.user_data['translate']
    if db.get_event_text(chat_id):
        await update.message.reply_text(translate('Error: An active event already exists.'))
        return ConversationHandler.END
    arg = parse_cmd_arg(update, context)
    context.user_data['new_event_data'] = {}
    if arg.strip().startswith('{'):
        try:
            context.user_data['new_event_data'] = parse_loose_json(arg)
            return await event_ask_step(update, context, EVENT_SET_NAME)
        except: pass
    if arg:
        context.user_data['new_event_data']['name'] = arg
        return await event_ask_step(update, context, EVENT_SET_LIMIT)
    await update.message.reply_text(translate("What is the name of the event?"), reply_markup=ForceReply(selective=True))
    return EVENT_SET_NAME

async def event_ask_step(update, context, step):
    translate = context.user_data['translate']
    data = context.user_data['new_event_data']
    query = update.callback_query

    if step == EVENT_SET_NAME:
        val = data.get('name')
        if val:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ " + translate("Confirm"), callback_data="CONF_NAME"), InlineKeyboardButton("✏️ " + translate("Change"), callback_data="CHG_NAME")]])
            txt = f"{translate('Event name')}: <b>{val}</b>. {translate('Confirm?')}"
            if query: await query.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            else: await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            return EVENT_SET_NAME
        else:
            thread_id = update.effective_message.message_thread_id if update.effective_message else None
            await context.bot.send_message(update.effective_chat.id, translate("What is the name of the event?"), reply_markup=ForceReply(selective=True), message_thread_id=thread_id)
            return EVENT_SET_NAME

    elif step == EVENT_SET_LIMIT:
        val = data.get('limit')
        if val:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ " + translate("Confirm"), callback_data="CONF_LIMIT"), InlineKeyboardButton("✏️ " + translate("Change"), callback_data="CHG_LIMIT")]])
            txt = f"{translate('Players limit')}: <b>{val}</b>. {translate('Confirm?')}"
            if query: await query.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            else: await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            return EVENT_SET_LIMIT
        else:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("14", callback_data="EV_LIMIT_14"), InlineKeyboardButton("16", callback_data="EV_LIMIT_16")], [InlineKeyboardButton("18", callback_data="EV_LIMIT_18"), InlineKeyboardButton("21", callback_data="EV_LIMIT_21")]])
            txt = translate("Select player limit (default 14):")
            if query: await query.edit_message_text(txt, reply_markup=kb)
            else: await update.message.reply_text(txt, reply_markup=kb)
            return EVENT_SET_LIMIT

    elif step == EVENT_SET_DATETIME:
        val = data.get('datetime')
        default_dt = get_default_datetime()
        default_str = default_dt.strftime('%Y-%m-%d %H:%M')
        if val:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ " + translate("Confirm"), callback_data="CONF_DT"), InlineKeyboardButton("✏️ " + translate("Change"), callback_data="CHG_DT")]])
            txt = f"{translate('Event date and time')}: <b>{val}</b>. {translate('Confirm?')}"
            if query: await query.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            else: await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            return EVENT_SET_DATETIME
        else:
            thread_id = update.effective_message.message_thread_id if update.effective_message else None
            await context.bot.send_message(update.effective_chat.id, f"{translate('Suggesting default time')}: <b>{default_str}</b>.\n{translate('Or enter custom time (e.g. tomorrow 20:30):')}", reply_markup=ForceReply(selective=True), parse_mode=ParseMode.HTML, message_thread_id=thread_id)
            await context.bot.send_message(update.effective_chat.id, translate("Use default time?"), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ {default_str}", callback_data="CONF_DEFAULT_DT")]]), message_thread_id=thread_id)
            return EVENT_SET_DATETIME

    elif step == EVENT_SET_PAYMENT:
        val = data.get('free')
        if val is not None:
            p_str = translate('Game for free') if val else translate('Paid')
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ " + translate("Confirm"), callback_data="CONF_PAY"), InlineKeyboardButton("✏️ " + translate("Change"), callback_data="CHG_PAY")]])
            txt = f"{translate('Payment type')}: <b>{p_str}</b>. {translate('Confirm?')}"
            if query: await query.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            else: await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            return EVENT_SET_PAYMENT
        else:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🆓 " + translate('Game for free'), callback_data="PAY_FREE")], [InlineKeyboardButton("💰 " + translate('Paid'), callback_data="PAY_PAID")]])
            txt = translate("Select payment type:")
            if query: await query.edit_message_text(txt, reply_markup=kb)
            else: await update.message.reply_text(txt, reply_markup=kb)
            return EVENT_SET_PAYMENT

    elif step == EVENT_SET_BLIK:
        val = data.get('blik')
        if val:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ " + translate("Confirm"), callback_data="CONF_BLIK"), InlineKeyboardButton("✏️ " + translate("Change"), callback_data="CHG_BLIK")]])
            txt = f"BLIK Phone: <b>{val}</b>. {translate('Confirm?')}"
            if query: await query.edit_message_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            else: await update.message.reply_text(txt, reply_markup=kb, parse_mode=ParseMode.HTML)
            return EVENT_SET_BLIK
        else:
            txt = translate("Please enter phone number for BLIK payments:")
            if query: await query.edit_message_text(txt)
            else: await update.message.reply_text(txt)
            return EVENT_SET_BLIK

    return ConversationHandler.END

@logger.catch
@make_translatable_user_id_context
async def event_name_handler(update, context):
    context.user_data['new_event_data']['name'] = update.message.text
    return await event_ask_step(update, context, EVENT_SET_LIMIT)

@logger.catch
@make_translatable_user_id_context
async def event_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = context.user_data['new_event_data']
    cb = query.data
    if cb == "CONF_NAME": return await event_ask_step(update, context, EVENT_SET_LIMIT)
    elif cb == "CHG_NAME": data['name'] = None; return await event_ask_step(update, context, EVENT_SET_NAME)
    elif cb == "CONF_LIMIT": return await event_ask_step(update, context, EVENT_SET_DATETIME)
    elif cb == "CHG_LIMIT": data['limit'] = None; return await event_ask_step(update, context, EVENT_SET_LIMIT)
    elif cb.startswith("EV_LIMIT_"): data['limit'] = int(cb.split("_")[-1]); return await event_ask_step(update, context, EVENT_SET_DATETIME)
    elif cb == "CONF_DT": return await event_ask_step(update, context, EVENT_SET_PAYMENT)
    elif cb == "CHG_DT": data['datetime'] = None; return await event_ask_step(update, context, EVENT_SET_DATETIME)
    elif cb == "CONF_DEFAULT_DT": data['datetime'] = get_default_datetime().strftime('%Y-%m-%d %H:%M'); return await event_ask_step(update, context, EVENT_SET_PAYMENT)
    elif cb == "CONF_PAY": 
        if data.get('free'): return await finalize_event_creation(update, context)
        return await event_ask_step(update, context, EVENT_SET_BLIK)
    elif cb == "CHG_PAY": data['free'] = None; return await event_ask_step(update, context, EVENT_SET_PAYMENT)
    elif cb == "PAY_FREE": data['free'] = True; return await finalize_event_creation(update, context)
    elif cb == "PAY_PAID": data['free'] = False; return await event_ask_step(update, context, EVENT_SET_BLIK)
    elif cb == "CONF_BLIK": return await finalize_event_creation(update, context)
    elif cb == "CHG_BLIK": data['blik'] = None; return await event_ask_step(update, context, EVENT_SET_BLIK)
    return ConversationHandler.END

@logger.catch
@make_translatable_user_id_context
async def event_datetime_handler(update, context):
    dt = parse_datetime(update.message.text, context.user_data['translate'])
    if dt:
        context.user_data['new_event_data']['datetime'] = dt.strftime('%Y-%m-%d %H:%M')
        return await event_ask_step(update, context, EVENT_SET_PAYMENT)
    else:
        await update.message.reply_text(context.user_data['translate']("Error: Could not parse date format."), reply_markup=ForceReply(selective=True))
        return EVENT_SET_DATETIME

@logger.catch
@make_translatable_user_id_context
async def event_blik_handler(update, context):
    context.user_data['new_event_data']['blik'] = update.message.text
    return await finalize_event_creation(update, context)

async def event_cancel(update, context):
    await update.message.reply_text(context.user_data.get('translate', lambda t: t)("Event creation cancelled."))
    return ConversationHandler.END

async def finalize_event_creation(update, context):
    data = context.user_data['new_event_data']
    translate = context.user_data['translate']
    chat_id = update.effective_chat.id
    name = data.get('name', 'Sport Event')
    limit = data.get('limit', 14)
    dt = parse_datetime(data.get('datetime'), translate) if data.get('datetime') else get_default_datetime()
    
    lists_thread_id = db.get_lists_thread_id(chat_id)
    if lists_thread_id is None and update.effective_message and update.effective_message.is_topic_message:
        lists_thread_id = update.effective_message.message_thread_id
    
    # Ensure chat is registered (FK constraint)
    db.register_new_chat_id(chat_id, 'ru')
    
    logger.info(f"Finalizing event creation for chat {chat_id} in thread {lists_thread_id}")
    placeholder = await context.bot.send_message(chat_id, f"🎉 <b>{name}</b>...", parse_mode=ParseMode.HTML, message_thread_id=lists_thread_id)
    logger.info(f"Placeholder created with message_id {placeholder.message_id}")
    
    try:
        db.event(chat_id, name, dt, limit, placeholder.message_id, "...", update.effective_user.id, location=data.get('location'))
        if data.get('blik'): db.set_event_blik_phone(chat_id, str(data.get('blik')))
    except Exception as e:
        logger.error(f"Failed to save event to DB: {e}")
        await context.bot.send_message(chat_id, f"❌ Error saving event: {e}", message_thread_id=lists_thread_id)
        return ConversationHandler.END
        
    full_text = create_event_full_text(chat_id, translate)
    await context.bot.edit_message_text(chat_id=chat_id, message_id=placeholder.message_id, text=full_text, reply_markup=build_message_markup(translate, None), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    db.save_latest_bot_message(chat_id, placeholder.message_id, full_text)
    event_id = db.get_event_id_by_chat_id(chat_id)
    if event_id: await log_event(chat_id, event_id, f"Event created: {name} (Limit: {limit}, Time: {dt})", context)
    msg = translate("Event created successfully!")
    if update.callback_query: await update.callback_query.message.reply_text(msg)
    else: await update.message.reply_text(msg)
    return ConversationHandler.END
