# -*- coding: utf-8 -*-
import json
import random
from loguru import logger
from telegram.constants import ParseMode
import sport_event_bot.db_postgres as db
import sport_event_bot.telegraph as tph
from sport_event_bot.utils.localization import make_translatable_user_id_context, TRANSLATIONS
from sport_event_bot.utils.logging_service import log_event
from sport_event_bot.ui.render import create_event_full_text
from sport_event_bot.ui.markups import build_message_markup, _serialize_inline_kb
from sport_event_bot.handlers.event_mgmt import show_info
from sport_event_bot.handlers.player import legioneer_added_message, legioneer_removed_message

@logger.catch
@make_translatable_user_id_context
async def button(update, context):
    query = update.callback_query
    if not query: return
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    translate = context.user_data['translate']
    db.add_or_update_user(user_id, query.from_user.first_name, query.from_user.last_name, query.from_user.username)

    data = query.data
    if data == "IGNORE":
        await query.answer()
        return
        
    if data == "ADD":
        db.apply_for_participation_in_the_event(chat_id, user_id)
        db.set_event_extra1(chat_id, None)
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id: await log_event(chat_id, event_id, f"User {query.from_user.first_name} joined event", context)
    elif data == "REMOVE":
        db.revoke_application_for_the_event(chat_id, user_id)
        db.set_event_extra1(chat_id, None)
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id: await log_event(chat_id, event_id, f"User {query.from_user.first_name} left event", context)
    elif data == "THINK":
        db.apply_for_thinking(chat_id, user_id)
        db.set_event_extra1(chat_id, None)
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id: await log_event(chat_id, event_id, f"User {query.from_user.first_name} is thinking", context)
    elif data == "ADD_LEGIONEER":
        db.apply_for_legioneer(chat_id, user_id)
        await legioneer_added_message(update, context)
        db.set_event_extra1(chat_id, None)
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id: await log_event(chat_id, event_id, f"User {query.from_user.first_name} added guest player", context)
    elif data == "REMOVE_LEGIONEER":
        db.revoke_for_legioneer(chat_id)
        await legioneer_removed_message(update, context)
        db.set_event_extra1(chat_id, None)
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id: await log_event(chat_id, event_id, f"User {query.from_user.first_name} removed guest player", context)
    elif data == "REMOVE_ALL_LEGIONEERS":
        db.revoke_all_user_legioneers(chat_id, user_id)
        db.set_event_extra1(chat_id, None)
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id: await log_event(chat_id, event_id, f"User {query.from_user.first_name} removed all guest players", context)
    elif data == "PAY":
        result = db.process_payment(chat_id, user_id)
        import os
        web_url = os.getenv('PAYMENTS_PAGE_URL', '')
        answer_msg = translate(result['message'])
        if web_url:
            answer_msg += f"\n{web_url}"
        await query.answer(answer_msg)
        if result['success']:
            event_id = db.get_event_id_by_chat_id(chat_id)
            if event_id:
                status = "confirmed payment" if "confirmed" in result['message'] else "revoked payment"
                await log_event(chat_id, event_id, f"User {query.from_user.first_name} {status}", context)
            try:
                entries = db.get_payment_log(chat_id)
                event_title = db.get_event_text(chat_id) or ''
                new_tph_url = await tph.publish_payment_log(event_title, entries, db.get_event_telegraph_url(chat_id))
                db.set_event_telegraph_url(chat_id, new_tph_url)
            except Exception as e: logger.warning(f"Telegraph update failed: {e}")
    elif data.startswith("SET_LIMIT_"):
        limit = int(data.split('_')[-1])
        db.set_players_limit(chat_id, limit)
        await query.answer(translate("Limit changed to %(limit)d") % {'limit': limit})
    elif data in ["SHUFFLE", "RESHUFFLE", "INC_TEAMS", "DEC_TEAMS"]:
        await handle_shuffle_callback(update, context, data)
    elif data.startswith("SET_LANG_"):
        new_lang = data.split("_")[-1]
        db.set_user_lang(user_id, new_lang)
        context.user_data['translate'] = TRANSLATIONS.get(new_lang, lambda t: t)
        await query.answer(context.user_data['translate']("Language updated"))
        await show_info(update, context)
        return

    full_text = create_event_full_text(chat_id, translate)
    kb = build_message_markup(translate, db.get_event_extra1(chat_id))
    try:
        await query.edit_message_text(text=full_text, reply_markup=kb, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        db.save_latest_bot_message(chat_id, query.message.message_id, full_text)
    except Exception as e:
        if "message is not modified" not in str(e).lower(): logger.exception(e)
    await query.answer()

async def handle_shuffle_callback(update, context, data):
    query = update.callback_query
    chat_id = query.message.chat_id
    translate = context.user_data['translate']
    players = db.get_event_users(chat_id) or []
    if not players:
        await query.answer(translate("No players to shuffle"))
        return
    num_teams = 2
    extra1 = db.get_event_extra1(chat_id)
    if extra1:
        try: num_teams = json.loads(extra1).get('num_teams', 2)
        except: pass
    if data == "INC_TEAMS": num_teams += 1
    elif data == "DEC_TEAMS": num_teams = max(2, num_teams - 1)
    limit = db.get_event_limit(chat_id)
    
    # players is a list of (user_id, invited_by)
    main_p = players[:limit] if limit > 0 else players
    res_p = players[limit:] if limit > 0 else []
    
    # We want to shuffle the players but keep their (uid, inviter) pairs
    random.shuffle(main_p)
    teams = {f"{translate('Team')} {i+1}": [] for i in range(num_teams)}
    for i, p in enumerate(main_p):
        teams[f"{translate('Team')} {(i % num_teams) + 1}"].append(p)
    db.set_event_extra1(chat_id, json.dumps({"num_teams": num_teams, "teams": teams, "reserve": res_p}, ensure_ascii=False))
