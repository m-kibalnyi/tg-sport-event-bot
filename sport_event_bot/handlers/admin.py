# -*- coding: utf-8 -*-
from loguru import logger

import sport_event_bot.db_postgres as db
import sport_event_bot.telegraph as tph
from sport_event_bot.handlers.event_mgmt import show_info
from sport_event_bot.ui.markups import build_penalty_markup, build_penalty_selection_markup
from sport_event_bot.utils.localization import make_translatable_user_id_context
from sport_event_bot.utils.auth import is_user_admin


async def _identify_user(update, context, translate, action_name):
    """
    Identifies a user from message reply, arguments, or interactive selection.
    Returns (user_id, days_or_none, markup_or_none)
    """
    chat_id = update.message.chat_id
    user_id = None
    days = None

    # 1. Check if it's a reply to a message
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        if context.args:
            try:
                days = int(context.args[0])
            except ValueError:
                pass
        return user_id, days, None

    # 2. Check arguments
    if context.args:
        arg = context.args[0]
        try:
            # Try as numeric ID
            user_id = int(arg)
            if len(context.args) > 1:
                try:
                    days = int(context.args[1])
                except ValueError:
                    pass
            return user_id, days, None
        except ValueError:
            # Not an ID, try searching by username or name
            if arg.startswith("@"):
                users = db.find_user_by_username(arg)
            else:
                # Join all args except the last one if the last one is a number (days)
                potential_days = None
                name_query = " ".join(context.args)
                if len(context.args) > 1:
                    try:
                        potential_days = int(context.args[-1])
                        name_query = " ".join(context.args[:-1])
                    except ValueError:
                        pass

                users = db.find_users_by_name(name_query)
                if potential_days is not None:
                    days = potential_days

            if len(users) == 1:
                user_id = users[0][0]
                return user_id, days, None
            elif len(users) > 1:
                players = []
                for uid, fn, ln, un in users:
                    name = f"{fn} {ln}".strip() or un or str(uid)
                    players.append((uid, name))
                
                kb = build_penalty_selection_markup(players, translate, action_name, str(days) if days else "")
                return None, None, kb
            else:
                await update.message.reply_text(translate("User not found."))
                return None, None, None

    # 3. If no user identified, show interactive selection from current event
    uids = db.get_event_users(chat_id)
    if not uids:
        return None, None, False # False indicates we should show usage

    players = []
    for uid, _ in uids:
        if uid < 1000:
            continue  # Skip guest players
        name = db.compose_full_name(uid)
        players.append((uid, name))

    if not players:
        return None, None, True # True indicates no participants found

    kb = build_penalty_selection_markup(players, translate, action_name, str(days) if days else "")
    return None, None, kb


@logger.catch
@make_translatable_user_id_context
async def set_players_limit(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

    try:
        limit = int(context.args[0])
        db.set_players_limit(chat_id, limit)
        await update.message.reply_text(translate("Players limit updated: %(limit)d") % {"limit": limit})
    except Exception:
        await update.message.reply_text(translate("Usage: /limit XX"))


@logger.catch
@make_translatable_user_id_context
async def show_stat(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

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
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

    user_id, days, result = await _identify_user(update, context, translate, "PEN_SEL")
    
    if user_id:
        if days is not None:
            # Honor the days provided in command
            try:
                db.penalty_for_user_in_chat(chat_id, user_id, update.effective_user.id, days)
                await update.message.reply_text(translate("Penalty applied for %(days)d days.") % {"days": days})
            except Exception as e:
                logger.exception(e)
                await update.message.reply_text(translate("Error applying penalty."))
        else:
            # User identified but no duration specified, ask for duration
            name = db.compose_full_name(user_id)
            from sport_event_bot.ui.markups import build_penalty_duration_markup
            await update.message.reply_text(
                translate("Select penalty duration for %(name)s:") % {"name": name},
                reply_markup=build_penalty_duration_markup(user_id, translate)
            )
    elif result is False:
        await update.message.reply_text(translate("Usage: /penalty [USER] or reply to a message."))
    elif result is True:
        await update.message.reply_text(translate("No participants found to penalty."))
    elif result:
        await update.message.reply_text(translate("Select player to penalty:"), reply_markup=result)


@logger.catch
@make_translatable_user_id_context
async def penalty_remove(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

    user_id, _, result = await _identify_user(update, context, translate, "PENALTY_REMOVE")
    
    if user_id:
        try:
            db.remove_user_penalties(chat_id, user_id)
            name = db.compose_full_name(user_id)
            await update.message.reply_text(translate("Penalty removed for %(name)s.") % {"name": name})
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text(translate("Error removing penalty."))
    elif result is False:
        await update.message.reply_text(translate("Usage: /penalty_remove [USER] or reply to a message."))
    elif result is True:
        await update.message.reply_text(translate("No participants found."))
    elif result:
        await update.message.reply_text(translate("Select player to remove penalty:"), reply_markup=result)


@logger.catch
@make_translatable_user_id_context
async def show_payments(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

    try:
        entries = db.get_payment_log(chat_id)
        if not entries:
            await update.message.reply_text(translate("No payments recorded yet."))
            return
        event_title = db.get_event_text(chat_id) or "Event"
        tph_url = await tph.publish_payment_log(event_title, entries, db.get_event_telegraph_url(chat_id))
        db.set_event_telegraph_url(chat_id, tph_url)
        await update.message.reply_text(f"💳 {translate('Payment log')}: {tph_url}")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(f"Error: {e}")


@logger.catch
@make_translatable_user_id_context
async def fix_ui(update, context):
    if not update.message:
        return
    if not await is_user_admin(update, context):
        translate = context.user_data["translate"]
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return
    await show_info(update, context)


@logger.catch
@make_translatable_user_id_context
async def set_lists_topic(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

    thread_id = update.message.message_thread_id
    db.set_lists_thread_id(chat_id, thread_id)
    await update.message.reply_text(translate("Lists topic configured for this thread."))


@logger.catch
@make_translatable_user_id_context
async def set_logs_topic(update, context):
    if not update.message:
        return
    chat_id = update.message.chat_id
    translate = context.user_data["translate"]
    if not await is_user_admin(update, context):
        await update.message.reply_text(translate("Access denied: only admins can use this command."))
        return

    thread_id = update.message.message_thread_id
    db.set_log_thread_id(chat_id, thread_id)
    await update.message.reply_text(translate("Logs topic configured for this thread."))
