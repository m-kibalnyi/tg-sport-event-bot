# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : KMiNT21 edited wavcheb 2024, updated by Grok 2025
# Created Date: 2022.
# Updated Date: April 2025
# version ='2.0'
# ---------------------------------------------------------------------------
"""Telegram BOT for organizing events with participant registration.
Updated to python-telegram-bot v22.x with asyncio.
Supports payment confirmation with 💰 emoji.
"""

import sys
import os
import datetime
import re
import signal
import gettext
import json
import socket
import parsedatetime
import urllib.request
import urllib.parse
import urllib.error
import random
from html.parser import HTMLParser
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env.development") # Load dev env first if exists
load_dotenv()

# Support both package mode and standalone mode
try:
    from . import db_postgres as db
    from . import telegraph as tph
except ImportError:
    import db_postgres as db
    import telegraph as tph
import asyncio
from typing import Optional, Callable
from functools import wraps
from loguru import logger
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from recurrent.event_parser import RecurringEvent
from telegram.error import BadRequest

# Bot directory paths
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(BOT_DIR, 'locale')

# Payments page URL from environment (replaces Telegraph if set)
PAYMENTS_PAGE_URL = os.getenv('PAYMENTS_PAGE_URL', '').strip()

# ==================== URL Metadata Parser ====================

class _MetaExtractor(HTMLParser):
    """Minimal HTML parser that extracts og:title or <title>."""
    def __init__(self):
        super().__init__()
        self.og_title = None
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            prop = d.get('property', '') or d.get('name', '')
            content = d.get('content', '')
            if prop == 'og:title' and content:
                self.og_title = content

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

def _parse_url_title_sync(url: str) -> str:
    """Fetch URL and return og:title or <title>. Runs synchronously."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content_type = resp.headers.get_content_type()
            if 'html' not in content_type:
                return ''
            raw = resp.read(65536)
            html = raw.decode('utf-8', errors='replace')
    except Exception:
        return ''
    parser = _MetaExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return (parser.og_title or parser.title or '').strip()

async def _fetch_url_title(url: str) -> str:
    """Async wrapper for URL title fetching (runs in thread pool)."""
    return await asyncio.to_thread(_parse_url_title_sync, url)

TRANSLATIONS = {
    'uk': gettext.translation('ua', localedir=LOCALE_DIR, languages=['uk']).gettext,
    'pt-br': gettext.translation('pt', localedir=LOCALE_DIR, languages=['pt_BR']).gettext,
    'ar': gettext.translation('ar', localedir=LOCALE_DIR, languages=['ar']).gettext,
    'ru': gettext.translation('ru', localedir=LOCALE_DIR, languages=['ru']).gettext
}

def _coerce_to_datetime(val: object) -> Optional[datetime.datetime]:
    """Accept datetime or str; return datetime or None."""
    if isinstance(val, datetime.datetime):
        return val
    if isinstance(val, str) and val.strip():
        s = val.strip()
        try:
            return datetime.datetime.fromisoformat(s)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.datetime.strptime(s, fmt)
                except ValueError:
                    pass
    return None


def make_translatable_user_id_context(func):
    """Декоратор для установки функции перевода в context.user_data"""
    @wraps(func)
    async def wrapped(update, context):
        user_id = None
        if update.message:
            user_id = update.message.from_user.id
        elif update.callback_query:
            user_id = update.callback_query.from_user.id

        lang = 'ru'  # Default to Russian
        if user_id:
            try:
                # 1. Start with 'ru' default or user preference
                db_lang = db.get_user_lang(user_id)
                if db_lang:
                    lang = db_lang
                else:
                    # 2. Fallback to Telegram language code if no preference
                    tg_lang = (update.message.from_user.language_code if update.message 
                               else update.callback_query.from_user.language_code)
                    if tg_lang in TRANSLATIONS:
                        lang = tg_lang
            except Exception as e:
                logger.warning(f"Language detection failed for user {user_id}: {e}")

        if lang in TRANSLATIONS:
            context.user_data['translate'] = TRANSLATIONS[lang]
        else:
            # English and other unsupported languages use original text
            context.user_data['translate'] = lambda text: text
            if lang != 'en':
                logger.info(f"No translation available for language: {lang}, using English")
        return await func(update, context)
    return wrapped

async def log_event(chat_id: int, event_id: int, message: str, context):
    """Log to DB, File, and Telegram topic if present"""
    db.add_event_log(event_id, message)
    
    # Also write to local file for PHP fallback
    try:
        log_dir = os.path.join(os.path.dirname(BOT_DIR), 'web', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'event_{event_id}.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception as e:
        logger.warning(f"Failed to write to file log: {e}")

    # Send to Telegram topic if available
    thread_id = db.get_log_thread_id(chat_id)
    if thread_id is not None and thread_id != 0:
        try:
            await context.bot.send_message(chat_id, f"📝 {message}", message_thread_id=thread_id)
        except Exception as e:
            logger.warning(f"Failed to send log to Telegram topic: {e}")

@make_translatable_user_id_context
async def set_log_topic(update, context):
    """Manually set the current topic as the log topic for this chat"""
    if not update.message:
        return
    if not update.message.is_topic_message:
        await update.message.reply_text("This command must be sent inside a forum topic.")
        return
    
    chat_id = update.message.chat_id
    thread_id = update.message.message_thread_id
    db.set_log_thread_id(chat_id, thread_id)
    translate = context.user_data['translate']
    await update.message.reply_text(translate("Log topic updated successfully."))
    logger.info(f"Log topic manually set for chat {chat_id} to thread {thread_id}")

@make_translatable_user_id_context
async def set_lists_topic(update, context):
    """Manually set the current topic as the lists topic for this chat"""
    if not update.message:
        return
    if not update.message.is_topic_message:
        await update.message.reply_text("This command must be sent inside a forum topic.")
        return
    
    chat_id = update.message.chat_id
    thread_id = update.message.message_thread_id
    db.set_lists_thread_id(chat_id, thread_id)
    translate = context.user_data['translate']
    await update.message.reply_text(translate("Lists topic updated successfully."))
    logger.info(f"Lists topic manually set for chat {chat_id} to thread {thread_id}")

async def forum_topic_created_handler(update, context):
    """Automatically detect 'Logs' and 'Lists' topics on creation"""
    if not update.message or not update.message.forum_topic_created:
        return
    name = update.message.forum_topic_created.name
    name_low = name.lower().strip()
    chat_id = update.message.chat_id
    thread_id = update.message.message_thread_id
    
    log_names = ['logs', 'журнал', 'логи', 'log', 'журнал\логи', 'notification', 'notifications']
    list_names = ['списки', 'lists', 'events', 'события', 'список', 'list', 'event']
    
    if any(n in name_low for n in log_names) or name_low in log_names:
        db.set_log_thread_id(chat_id, thread_id)
        logger.info(f"Automatically detected and set log topic for chat {chat_id}: {name} ({thread_id})")
    elif any(n in name_low for n in list_names) or name_low in list_names:
        db.set_lists_thread_id(chat_id, thread_id)
        logger.info(f"Automatically detected and set lists topic for chat {chat_id}: {name} ({thread_id})")

	
def _serialize_inline_kb(kb: InlineKeyboardMarkup) -> str:
    if not kb or not kb.inline_keyboard:
        return ""
    rows = []
    for row in kb.inline_keyboard:
        rows.append("|".join(f"{btn.text}::{btn.callback_data or btn.url or ''}" for btn in row))
    return "\n".join(rows)

KNOWN_CHAT_IDS = set()

def new_chat_id_memoization(chat_id: int, lang: str):
    global KNOWN_CHAT_IDS
    if chat_id not in KNOWN_CHAT_IDS:
        KNOWN_CHAT_IDS.add(chat_id)
        db.register_new_chat_id(chat_id, lang)
        logger.info(f'New chat_id: {chat_id}')

@logger.catch
def build_message_markup(translate_func: Callable[[str], str], extra1: Optional[str] = None):
    """Создание кнопок с использованием переданной функции перевода"""
    rows = [
        # Row 1: Close and Shuffle
        [
            InlineKeyboardButton("🧒 " + translate_func('Close collection'), callback_data='CLOSE_EVENT'),
            InlineKeyboardButton("🔀 " + (translate_func('Shuffle (reshuffle)') if extra1 else translate_func('Shuffle (перемешать)')), 
                                 callback_data='RESHUFFLE' if extra1 else 'SHUFFLE')
        ],
        # Row 2: Participation status
        [
            InlineKeyboardButton("✅ " + translate_func('I am going'), callback_data='ADD'),
            InlineKeyboardButton("❌ " + translate_func('I am not going'), callback_data='REMOVE'),
            InlineKeyboardButton("🤔 " + translate_func('Thinking'), callback_data='THINK')
        ],
        # Row 3: Legioneers
        [
            InlineKeyboardButton(translate_func('Plus +'), callback_data='ADD_LEGIONEER'),
            InlineKeyboardButton(translate_func('Minus -'), callback_data='REMOVE_LEGIONEER'),
            InlineKeyboardButton(translate_func('- All'), callback_data='REMOVE_ALL_LEGIONEERS')
        ],
        # Row 4: Payment
        [
            InlineKeyboardButton(translate_func('💰 Payment confirmed'), callback_data='PAY')
        ]
    ]
    
    # Optional team adjustment buttons (only if shuffled)
    if extra1:
        rows.append([
            InlineKeyboardButton(translate_func('Team count (+1)'), callback_data='INC_TEAMS'),
            InlineKeyboardButton(translate_func('Team count (-1)'), callback_data='DEC_TEAMS')
        ])
        
    # Row 5/6: Admin player limit change
    rows.append([
        InlineKeyboardButton(translate_func('Limit: 14'), callback_data='SET_LIMIT_14'),
        InlineKeyboardButton(translate_func('Limit: 16'), callback_data='SET_LIMIT_16'),
        InlineKeyboardButton(translate_func('Limit: 21'), callback_data='SET_LIMIT_21')
    ])
        
    return InlineKeyboardMarkup(rows)

@logger.catch
@make_translatable_user_id_context
async def button(update, context):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    this_chat_id = query.message.chat_id
    user_id = query.from_user.id
    translate = context.user_data['translate']
    db.add_or_update_user(user_id, query.from_user.first_name, query.from_user.last_name, query.from_user.username)

    if query.data == "ADD":
        db.apply_for_participation_in_the_event(this_chat_id, user_id)
        db.set_event_extra1(this_chat_id, None) # Clear shuffle on change
        event_id = db.get_event_id_by_chat_id(this_chat_id)
        if event_id: await log_event(this_chat_id, event_id, f"User {query.from_user.first_name} applied", context)
    elif query.data == "REMOVE":
        db.revoke_application_for_the_event(this_chat_id, user_id)
        db.set_event_extra1(this_chat_id, None) # Clear shuffle on change
        event_id = db.get_event_id_by_chat_id(this_chat_id)
        if event_id: await log_event(this_chat_id, event_id, f"User {query.from_user.first_name} removed application", context)
    elif query.data == "ADD_LEGIONEER":
        db.apply_for_legioneer(this_chat_id, user_id)
        await legioneer_added_message(update, context)
        db.set_event_extra1(this_chat_id, None) # Clear shuffle on change
        event_id = db.get_event_id_by_chat_id(this_chat_id)
        if event_id: await log_event(this_chat_id, event_id, f"User {query.from_user.first_name} added a legioneer", context)
    elif query.data == "REMOVE_LEGIONEER":
        db.revoke_for_legioneer(this_chat_id)
        await legioneer_removed_message(update, context)
        db.set_event_extra1(this_chat_id, None) # Clear shuffle on change
        event_id = db.get_event_id_by_chat_id(this_chat_id)
        if event_id: await log_event(this_chat_id, event_id, f"User {query.from_user.first_name} removed a legioneer", context)
    elif query.data == "THINK":
        db.apply_for_thinking(this_chat_id, user_id)
        db.set_event_extra1(this_chat_id, None)
        event_id = db.get_event_id_by_chat_id(this_chat_id)
        if event_id: await log_event(this_chat_id, event_id, f"User {query.from_user.first_name} is thinking", context)
    elif query.data == "REMOVE_ALL_LEGIONEERS":
        db.revoke_all_user_legioneers(this_chat_id, user_id)
        db.set_event_extra1(this_chat_id, None)
    elif query.data == "CLOSE_EVENT":
        # Check permissions: owner or admin
        creator_id = db.get_event_creator(this_chat_id)
        is_creator = user_id == creator_id
        is_admin = False
        try:
            member = await context.bot.get_chat_member(this_chat_id, user_id)
            if member.status in ['creator', 'administrator']:
                is_admin = True
        except:
            pass
            
        if is_creator or is_admin:
            await remove_all_chat_events(update, context)
            return # remove_all_chat_events handles the message update
        else:
            await query.answer(translate("Only admins or event creator can close the collection"), show_alert=True)
            return

    elif query.data == "PAY":
        result = db.process_payment(this_chat_id, user_id)
        await query.answer(translate(result['message']))
        if result['success']:
            # Log payment
            event_id = db.get_event_id_by_chat_id(this_chat_id)
            if event_id:
                status_text = "confirmed payment" if "confirmed" in result['message'] else "revoked payment"
                await log_event(this_chat_id, event_id, f"User {query.from_user.first_name} {status_text}", context)
            
            # Update Telegraph payment log page
            try:
                entries = db.get_payment_log(this_chat_id)
                event_title = db.get_event_text(this_chat_id) or ''
                existing_url = db.get_event_telegraph_url(this_chat_id)
                new_tph_url = await tph.publish_payment_log(event_title, entries, existing_url)
                db.set_event_telegraph_url(this_chat_id, new_tph_url)
            except Exception as e:
                logger.warning(f"Telegraph update failed: {e}")

    elif query.data in ["SET_LIMIT_14", "SET_LIMIT_16", "SET_LIMIT_21"]:
        # Check permissions: owner or admin
        creator_id = db.get_event_creator(this_chat_id)
        is_creator = user_id == creator_id
        is_admin = False
        try:
            member = await context.bot.get_chat_member(this_chat_id, user_id)
            if member.status in ['creator', 'administrator']:
                is_admin = True
        except:
            pass

        if is_creator or is_admin:
            new_limit = int(query.data.split('_')[-1])
            db.set_players_limit(this_chat_id, new_limit)
            await query.answer(translate("Limit changed to %(limit)d") % {'limit': new_limit})
            event_id = db.get_event_id_by_chat_id(this_chat_id)
            if event_id: await log_event(this_chat_id, event_id, f"Players limit changed to {new_limit} by {query.from_user.first_name}", context)
        else:
            await query.answer(translate("Only admins or event creator can change the limit"), show_alert=True)
            return
    
    elif query.data in ["SHUFFLE", "RESHUFFLE", "INC_TEAMS", "DEC_TEAMS"]:
        players = db.get_event_users(this_chat_id) or []
        if players:
            extra1 = db.get_event_extra1(this_chat_id)
            num_teams = 2
            if extra1:
                try:
                    data = json.loads(extra1)
                    num_teams = data.get('num_teams', 2)
                except:
                    pass
            
            if query.data == "INC_TEAMS":
                num_teams += 1
            elif query.data == "DEC_TEAMS":
                num_teams = max(2, num_teams - 1)
            
            # Split players into main and reserve based on limit
            limit = db.get_event_limit(this_chat_id)
            if limit > 0 and len(players) > limit:
                main_players = players[:limit]
                reserve_players = players[limit:]
            else:
                main_players = players
                reserve_players = []

            random.shuffle(main_players)
            teams = {}
            for i in range(num_teams):
                team_name = f"{translate('Team')} {i+1}"
                teams[team_name] = []
            
            for i, p in enumerate(main_players):
                team_idx = i % num_teams
                team_name = f"{translate('Team')} {team_idx+1}"
                teams[team_name].append(p)
            
            new_data = {"num_teams": num_teams, "teams": teams, "reserve": reserve_players}
            db.set_event_extra1(this_chat_id, json.dumps(new_data, ensure_ascii=False))
            event_id = db.get_event_id_by_chat_id(this_chat_id)
            if event_id: await log_event(this_chat_id, event_id, f"Players shuffled into {num_teams} teams by {query.from_user.first_name}", context)
        else:
            await query.answer(translate("No players to shuffle"))

    payment_url = db.get_event_payment_url(this_chat_id)
    telegraph_url = db.get_event_telegraph_url(this_chat_id)
    extra1 = db.get_event_extra1(this_chat_id)
    message_text = create_event_full_text(this_chat_id, translate, payment_url, telegraph_url)
    safe_text = (message_text or "").strip() or " "
    new_kb = build_message_markup(translate, extra1)
    new_kb_sig = _serialize_inline_kb(new_kb)

    # Текущее сохранённое состояние
    prev_text = (db.get_latest_bot_message_text(this_chat_id) or "").strip()
    # Получить текущую разметку у сообщения
    try:
        current_msg = query.message
        cur_kb = current_msg.reply_markup
    except Exception:
        cur_kb = None
    cur_kb_sig = _serialize_inline_kb(cur_kb)

    text_changed = safe_text != prev_text
    kb_changed = new_kb_sig != cur_kb_sig

    if text_changed or kb_changed:
        try:
            await query.edit_message_text(
                text=safe_text,
                reply_markup=new_kb,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            db.save_latest_bot_message(this_chat_id, query.message.message_id, safe_text)
        except Exception as e:
            # Игнорировать "message is not modified"
            if "message is not modified" in str(e).lower():
                pass
            else:
                logger.exception(e)

    # Removed cross-platform sync logic

    elif query.data.startswith("SET_LANG_"):
        new_lang = query.data.split("_")[-1]
        db.set_user_lang(user_id, new_lang)
        context.user_data['translate'] = TRANSLATIONS.get(new_lang, lambda t: t)
        await query.answer(context.user_data['translate']("Language updated"))
        await show_info(update, context)

    await query.answer()

@logger.catch
def parse_datetime(str_datetime_in_free_form: str, translate: Callable[[str], str]) -> Optional[datetime.datetime]:
    consts = parsedatetime.Constants(localeID=translate('en_US'), usePyICU=False)
    consts.use24 = True
    r_event = RecurringEvent(parse_constants=consts)
    found_date = r_event.parse(str_datetime_in_free_form)
    if not found_date:
        return None
    delta = found_date - datetime.datetime.now()
    if delta.days < 0 or delta.days > 31:
        logger.info(f"Invalid time delta: {delta.days} days")
        return None
    return found_date

@logger.catch
def parse_cmd_arg(update, _context) -> str:
    if not update.message or not update.message.text:
        return ''
    user_input = update.message.text.strip()
    space_index = user_input.find(' ')
    if space_index < 0:
        return ''
    cmd_arg = user_input[space_index + 1:].strip()
    return cmd_arg.replace('@nashfootballbot', '').strip()

@logger.catch
async def remove_all_chat_events(update, context):
    query = update.callback_query
    if query:
        msg = query.message
        user = query.from_user
    else:
        msg = update.message
        user = update.message.from_user if update.message else None

    if not msg:
        return

    this_chat_id = msg.chat_id
    lang = (user.language_code if user else 'ru') or 'ru'
    new_chat_id_memoization(this_chat_id, lang)
    
    latest_bot_message_id = db.get_latest_bot_message_id(this_chat_id)
    if latest_bot_message_id and db.get_event_text(this_chat_id):
        # Render closed-state text (strikethrough) before actually closing the event
        translate = TRANSLATIONS.get(lang, lambda t: t)
        try:
            payment_url = db.get_event_payment_url(this_chat_id)
            telegraph_url = db.get_event_telegraph_url(this_chat_id)
            closed_text = create_event_full_text(
                this_chat_id, translate, payment_url, telegraph_url, closed=True
            ).strip() or " "
            await context.bot.edit_message_text(
                chat_id=this_chat_id,
                message_id=latest_bot_message_id,
                text=closed_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            db.save_latest_bot_message(this_chat_id, latest_bot_message_id, closed_text)
        except Exception as e:
            logger.warning(f"Failed to mark event as closed: {e}")
            # Fallback: at least clear the inline keyboard
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=this_chat_id, message_id=latest_bot_message_id
                )
            except Exception as e2:
                logger.warning(f"Failed to clear reply markup: {e2}")
    event_id = db.get_event_id_by_chat_id(this_chat_id)
    if event_id:
        await log_event(this_chat_id, event_id, f"Event closed by {user.first_name if user else 'system'}", context)
    db.close_all_open_events_for_chat(this_chat_id)

@logger.catch
@make_translatable_user_id_context
async def create_new_event(update, context):
    """Создание нового события с проверкой аргументов и активных событий"""
    if not update.message:
        return
    this_chat_id = update.message.chat_id
    lang = update.message.from_user.language_code
    translate = context.user_data['translate']
    if lang:
        db.set_chat_lang(this_chat_id, lang)

    event_text = parse_cmd_arg(update, context)
    if not event_text:
        await update.message.reply_text(translate('Error: Please provide an event description. Usage: /event TEXT'))
        return

    if db.get_event_text(this_chat_id):
        await update.message.reply_text(translate('Error: An active event already exists. Close it with /event_remove first.'))
        return

    # Extract payment URL from event text and store separately
    payment_url = None
    url_match = re.search(r'https?://\S+', event_text)
    if url_match:
        payment_url = url_match.group().rstrip('.,)')
        before = event_text[:url_match.start()].strip()
        after = event_text[url_match.end():].strip()
        event_text = ' '.join(filter(None, [before, after])).strip()

    txt = event_text.lower()
    limit_markers = ['maximum', 'max', 'limit', 'максимум', 'максимальн', 'макс', 'лимит', 'ограничени', 'до']
    event_limit = 14
    for marker in limit_markers:
        if marker in txt:
            try:
                number = re.search(marker + r'[\s\S]*?(\d+)', txt).group(1)
                event_limit = int(number)
            except:
                continue
    event_datetime = parse_datetime(event_text, translate)
    message_text = translate("New event created") + ":\n\n🎉<b> " + event_text + " </b>🎉"
    if payment_url:
        message_text += f'\n\n<a href="{payment_url}">{translate("💳 Payment link")}</a>'
    if not message_text.strip():
        message_text = " "
    # Send to specific topic if available
    lists_thread_id = db.get_lists_thread_id(this_chat_id)
    # Default to current topic if no default is set in DB
    if lists_thread_id is None and update.message.is_topic_message:
        lists_thread_id = update.message.message_thread_id
    
    new_message = await context.bot.send_message(
        this_chat_id, message_text,
        reply_markup=build_message_markup(translate, None),
        parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        message_thread_id=lists_thread_id
    )
    db.event(this_chat_id, event_text, event_datetime, event_limit, new_message.message_id, message_text, update.message.from_user.id)
    event_id = db.get_event_id_by_chat_id(this_chat_id)
    if event_id:
        await log_event(this_chat_id, event_id, f"Event created: {event_text}", context)
    if payment_url:
        db.set_event_payment_url(this_chat_id, payment_url)

@logger.catch
async def update_event(update, context):
    if not update.message:
        return
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    new_event_text = parse_cmd_arg(update, context)
    db.update_event_text(update.message.chat_id, new_event_text)
    await show_info(update, context)

@logger.catch
async def set_event_datetime(update, context):
    if not update.message:
        return
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    str_datetime_in_free_form = parse_cmd_arg(update, context)
    translate = context.user_data['translate']
    event_datetime = parse_datetime(str_datetime_in_free_form, translate)
    if event_datetime:
        db.set_event_datetime(update.message.chat_id, event_datetime)
    await show_info(update, context)

@logger.catch
async def set_players_limit(update, context):
    if not update.message:
        return
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    try:
        new_limit = parse_cmd_arg(update, context)
        db.set_players_limit(update.message.chat_id, int(new_limit))
    except Exception as e:
        logger.exception(e)

@logger.catch
def create_event_full_text(this_chat_id: int, translate: Callable[[str], str],
                           payment_url: str = None, telegraph_url: str = None,
                           closed: bool = False):
    def player_name_with_cards(games_registered, penalties, full_name, translator):
        return full_name

    def _wrap_closed(s: str) -> str:
        return f'<s>{s}</s>' if closed else s

    event_title = db.get_event_text(this_chat_id) or ""
    if closed:
        text = f'🎉"<s><b>{event_title}</b></s>"🎉  🔒 <i>{translate("Event closed")}</i>\n'
    else:
        text = '🎉"<b>' + event_title + '</b>"🎉\n'
    players_limit = db.get_event_limit(this_chat_id) or 0
    if players_limit:
        text += translate('Players limit') + f': {players_limit}\n'
    raw_dt = db.get_event_datetime(this_chat_id)
    event_datetime = _coerce_to_datetime(raw_dt)
    if event_datetime:
        text += '📅 ' + translate('Event date and time') + f": {event_datetime.strftime('%Y-%m-%d, %H:%M')}\n"
        now = datetime.datetime.now()
        if event_datetime < now:
            text += '⏳ ' + translate('Event time out') + '.\n'
        else:
            delta = event_datetime - now
            hours = round(delta.seconds / 3600)
            text += '⏳ ' + translate('Time left') + f': {delta.days} ' + translate('days') + ' ' + translate('and') + f' {hours} ' + translate('hours') + '\n'

    # Payment links above players list
    links = []
    if payment_url:
        links.append(f'<a href="{payment_url}">{translate("💳 Payment link")}</a>')
    # Use PAYMENTS_PAGE_URL if configured, otherwise fall back to Telegraph
    if PAYMENTS_PAGE_URL:
        try:
            event_id = db.get_event_id_by_chat_id(this_chat_id)
            payments_link = f'{PAYMENTS_PAGE_URL}?event={event_id}'
            links.append(f'<a href="{payments_link}">{translate("Current payments")}</a>')
        except:
            pass
    elif telegraph_url:
        links.append(f'<a href="{telegraph_url}">{translate("Current payments")}</a>')
    
    # BLIK Phone
    blik_phone = db.get_event_blik_phone(this_chat_id)
    if blik_phone:
        links.append(f'<b>BLIK:</b> <code>{blik_phone}</code>')

    if links:
        text += ' | '.join(links) + '\n\n'

    text += translate('Players list') + ':\n'
    text_players = ''
    players = db.get_event_users(this_chat_id) or []
    
    extra1 = db.get_event_extra1(this_chat_id)
    teams_data = None
    if extra1:
        try:
            teams_data = json.loads(extra1)
        except Exception:
            pass

    if teams_data and 'teams' in teams_data:
        # Render grouped by teams
        for team_name, player_ids in teams_data['teams'].items():
            text_players += f"\n<b>{team_name}:</b>\n"
            for i, uid in enumerate(player_ids, 1):
                full_name = db.compose_full_name(uid)
                # Determine emoji: ✅ for regular, ➕ for legioneer (10-1009)
                emoji = "➕ " if 10 <= uid < 1010 else "✅ "
                
                # Check for cards/penalties
                games, penalties = db.get_chat_user_rp(this_chat_id, uid)
                printable_name = player_name_with_cards(games, penalties, full_name, translate)
                
                text_players += f"  {i}. {emoji}{printable_name}\n"
        
        # Render reserve if available in shuffled state
        reserve_ids = teams_data.get('reserve', [])
        if reserve_ids:
            text_players += f"\n=====================\n{translate('RESERVE')}:\n"
            for i, uid in enumerate(reserve_ids, 1):
                full_name = db.compose_full_name(uid)
                emoji = "➕ " if 10 <= uid < 1010 else "✅ "
                games, penalties = db.get_chat_user_rp(this_chat_id, uid)
                printable_name = player_name_with_cards(games, penalties, full_name, translate)
                text_players += f"  {i}. {emoji}{printable_name}\n"
    else:
        # Render plain list
        for i, uid in enumerate(players, 1):
            if players_limit and i == players_limit + 1:
                text_players += f"\n=====================\n{translate('RESERVE')}:\n"

            full_name = db.compose_full_name(uid)
            # Determine emoji
            emoji = "➕ " if 10 <= uid < 1010 else "✅ "
            
            # Check for cards/penalties
            games, penalties = db.get_chat_user_rp(this_chat_id, uid)
            printable_name = player_name_with_cards(games, penalties, full_name, translate)
            
            # Application number
            prefix = f"{i}. "
            
            text_players += f"{prefix}{emoji}{printable_name}\n"

    text += '\n' + text_players
    total_players = len(players)
    # Not going list
    not_going_players = db.get_event_revoked_users(this_chat_id) or []
    if not_going_players:
        text += '\n\n=====================\n\n' + translate('I am not going') + ':\n'
        for i, uid in enumerate(not_going_players, 1):
            full_name = db.compose_full_name(uid)
            text += f"{i}. ❌ {full_name}\n"
    elif total_players == 0:
        text += '\n' + translate('No applications yet')

    # Thinking list
    thinking_players = db.get_thinking_users(this_chat_id) or []
    if thinking_players:
        text += '\n\n=====================\n\n' + translate('Thinking') + ':\n'
        for i, uid in enumerate(thinking_players, 1):
            full_name = db.compose_full_name(uid)
            text += f"{i}. 🤔 {full_name}\n"

    # Yellow cards section
    active_penalties = db.get_active_penalties(this_chat_id)
    if active_penalties:
        text += '\n\n=====================\n\n' + translate('Yellow Cards') + ' 🟨:\n'
        for i, pen in enumerate(active_penalties, 1):
            nm = pen['full_name']
            expiry = pen['expires_at']
            if expiry:
                delta = expiry - datetime.datetime.now()
                days_left = max(0, delta.days)
                text += f"{i}. 🟨 {nm} ({translate('expires in')} {days_left} {translate('days')})\n"
            else:
                text += f"{i}. 🟨 {nm}\n"

    safe = text.strip()
    return safe if safe else " "

@logger.catch
@make_translatable_user_id_context
async def show_info(update, context):
    if not update.message:
        return
    this_chat_id = update.message.chat_id
    translate = context.user_data['translate']
    new_chat_id_memoization(this_chat_id, update.message.from_user.language_code)
    if not db.get_event_text(this_chat_id):
        await update.message.reply_text(translate('No events'))
        return
    payment_url = db.get_event_payment_url(this_chat_id)
    telegraph_url = db.get_event_telegraph_url(this_chat_id)
    extra1 = db.get_event_extra1(this_chat_id)
    event_text = create_event_full_text(this_chat_id, translate, payment_url, telegraph_url).strip() or " "
    latest_bot_message_id = db.get_latest_bot_message_id(this_chat_id)
    if latest_bot_message_id:
        try:
            await context.bot.edit_message_reply_markup(chat_id=this_chat_id, message_id=latest_bot_message_id)
        except Exception as e:
            logger.warning(f"Failed to clear reply markup: {e}")
    new_message = await context.bot.send_message(
        this_chat_id, event_text,
        reply_markup=build_message_markup(translate, extra1),
        parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        message_thread_id=db.get_lists_thread_id(this_chat_id) or (update.message.message_thread_id if update.message else None)
    )
    db.save_latest_bot_message(this_chat_id, new_message.message_id, event_text)

@logger.catch
@make_translatable_user_id_context
async def add_player(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    user = update.message.from_user
    if db.get_event_text(update.message.chat_id):
        db.add_or_update_user(user.id, user.first_name, user.last_name, user.username)
        db.apply_for_participation_in_the_event(update.message.chat_id, user.id)
        logger.info(f"Event - Player applied: {user.id}")
        event_id = db.get_event_id_by_chat_id(update.message.chat_id)
        if event_id:
            await log_event(update.message.chat_id, event_id, f"User {user.first_name} applied via command", context)
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def remove_player(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    user = update.message.from_user
    if db.get_event_text(update.message.chat_id):
        db.add_or_update_user(user.id, user.first_name, user.last_name, user.username)
        db.revoke_application_for_the_event(update.message.chat_id, user.id)
        logger.info(f"Event - Player revoked: {user.id}")
        event_id = db.get_event_id_by_chat_id(update.message.chat_id)
        if event_id:
            await log_event(update.message.chat_id, event_id, f"User {user.first_name} revoked application via command", context)
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def add_legioneer(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    chat_id = update.message.chat_id
    if db.get_event_text(chat_id):
        await legioneer_added_message(update, context)
        db.apply_for_legioneer(chat_id, update.message.from_user.id)
        logger.info(f"Event - Legioneer applied in chat: {chat_id}")
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def remove_legioneer(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    chat_id = update.message.chat_id
    if db.get_event_text(chat_id):
        await legioneer_removed_message(update, context)
        db.revoke_for_legioneer(chat_id)
        logger.info(f"Event - Legioneer removed in chat: {chat_id}")
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def legioneer_added_message(update, context):
    translate = context.user_data['translate']
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    full_name = db.compose_full_name(user_id)
    if db.get_event_text(chat_id):
        # We only log to specific Logs topic now to avoid duplication in General
        event_id = db.get_event_id_by_chat_id(chat_id)
        if event_id:
             await log_event(chat_id, event_id, f"Guest player applied by {full_name}", context)

@logger.catch
@make_translatable_user_id_context
async def legioneer_removed_message(update, context):
    translate = context.user_data['translate']
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    full_name = db.compose_full_name(user_id)
    event_id = db.get_event_id_by_chat_id(chat_id)
    if event_id and db.get_legioneer_user(event_id) > 9 and db.get_event_text(chat_id):
        # We only log to specific Logs topic now to avoid duplication in General
        await log_event(chat_id, event_id, f"Guest player was revoked by {full_name}", context)

@logger.catch
@make_translatable_user_id_context
async def confirm_payment(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    this_chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    new_chat_id_memoization(this_chat_id, update.message.from_user.language_code)
    if not db.get_event_text(this_chat_id):
        await update.message.reply_text(translate('No active event found.'))
        return
    result = db.process_payment(this_chat_id, user_id)
    await update.message.reply_text(translate(result['message']))
    if result['success']:
        event_id = db.get_event_id_by_chat_id(this_chat_id)
        if event_id:
            status_text = "confirmed payment" if "confirmed" in result['message'] else "revoked payment"
            await log_event(this_chat_id, event_id, f"User {update.message.from_user.first_name} {status_text}", context)
        await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def penalty_player(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    
    args = parse_cmd_arg(update, context).split()
    if not args:
        await update.message.reply_text(translate('Error: Please provide a user ID. Usage: /penalty USERID [TTL_DAYS]'))
        return
    
    user_id_str = args[0]
    try:
        user_id_int = int(user_id_str)
    except ValueError:
        await update.message.reply_text(translate('Error: User ID must be a number. Usage: /penalty USERID [TTL_DAYS]'))
        return

    ttl_days = 14
    if len(args) > 1:
        try:
            ttl_days = int(args[1])
        except ValueError:
            await update.message.reply_text(translate('Error: TTL days must be a number.'))
            return

    try:
        db.penalty_for_user_in_chat(update.message.chat_id, user_id_int, update.message.from_user.id, ttl_days)
        full_name = db.compose_full_name(user_id_int)
        penalty_text = translate('The player %(full_name)s was handed a yellow card for non-appearance') % {'full_name': full_name}
        if ttl_days != 14:
            penalty_text += f" ({translate('expires in')} {ttl_days} {translate('days')})"
        await context.bot.send_message(
            update.message.chat_id, penalty_text, parse_mode=ParseMode.HTML,
            message_thread_id=update.message.message_thread_id
        )
        logger.info(f"Penalty applied to user {user_id_int} in chat {update.message.chat_id} with TTL {ttl_days}")
        
        # Also log to Logs topic
        event_id = db.get_event_id_by_chat_id(update.message.chat_id)
        if event_id:
            await log_event(update.message.chat_id, event_id, penalty_text, context)
            
        await show_info(update, context) # Refresh event message
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text(translate('Error applying penalty.'))

@logger.catch
@make_translatable_user_id_context
async def fix_squad(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    this_chat_id = update.message.chat_id
    if not db.get_event_text(this_chat_id):
        await update.message.reply_text(translate('No events to fix stat for'))
        return
    text = translate('Current statistics for this chat room members:') + '\n<code>'
    squad = []
    players_limit = db.get_event_limit(this_chat_id)
    for position, userid in enumerate(db.get_event_users(this_chat_id), start=1):
        if not players_limit or position <= players_limit:
            try:
                squad.append(userid)
                full_name = db.compose_full_name(userid)
                games, penalties = db.get_chat_user_rp(this_chat_id, userid)
                games += 1
                text += f"{full_name} {games}/{penalties}\n"
            except Exception as e:
                logger.exception(e)
    text += "</code>"
    latest_bot_message_id = db.get_latest_bot_message_id(this_chat_id)
    if latest_bot_message_id:
        # Mark existing event message as closed (strikethrough) before closing in DB
        try:
            payment_url = db.get_event_payment_url(this_chat_id)
            telegraph_url = db.get_event_telegraph_url(this_chat_id)
            closed_text = create_event_full_text(
                this_chat_id, translate, payment_url, telegraph_url, closed=True
            ).strip() or " "
            await context.bot.edit_message_text(
                chat_id=this_chat_id,
                message_id=latest_bot_message_id,
                text=closed_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            db.save_latest_bot_message(this_chat_id, latest_bot_message_id, closed_text)
        except Exception as e:
            logger.warning(f"Failed to mark event as closed on /fix: {e}")
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=this_chat_id, message_id=latest_bot_message_id
                )
            except Exception as e2:
                logger.warning(f"Failed to clear reply markup: {e2}")
    await context.bot.send_message(
        this_chat_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        message_thread_id=(update.message.message_thread_id if update.message else None)
    )
    db.fix_event(this_chat_id)

@logger.catch
@make_translatable_user_id_context
async def show_stat(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    all_userids = db.get_only_chat_participants(update.message.chat_id)
    if not all_userids:
        return
    text = translate('Current statistics for this chat room members:') + '\n'
    text += translate('Registrations / Penalties') + '\n<code>'
    for userid in all_userids:
        if 10 <= userid < 1010:
            continue
        printable_name = db.compose_full_name(userid)
        registered, penalties = db.get_chat_user_rp(update.message.chat_id, userid)
        text += f"ID:{userid}, {registered:>2}/{penalties}, Full Name: {printable_name}\n"
    text += '</code>'
    await context.bot.send_message(
        update.message.chat_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        message_thread_id=update.message.message_thread_id
    )

@logger.catch
@make_translatable_user_id_context
async def show_payments(update, context):
    """Publish payment log to Telegraph and send the link (/payments command)."""
    if not update.message:
        return
    this_chat_id = update.message.chat_id
    translate = context.user_data['translate']
    new_chat_id_memoization(this_chat_id, update.message.from_user.language_code)
    event_title = db.get_event_text(this_chat_id)
    if not event_title:
        await update.message.reply_text(translate('No active event found.'))
        return
    entries = db.get_payment_log(this_chat_id)
    try:
        existing_url = db.get_event_telegraph_url(this_chat_id)
        page_url = await tph.publish_payment_log(event_title, entries, existing_url)
        db.set_event_telegraph_url(this_chat_id, page_url)
        count = len(entries)
        await update.message.reply_text(
            f'💰 <b>{translate("Payment log")}</b> ({count} {translate("records")}):\n{page_url}',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
    except Exception as e:
        logger.error(f"Telegraph publish failed: {e}")
        # Fallback: show inline
        if not entries:
            await update.message.reply_text(translate('No payment records yet.'))
            return
        lines = [f'💰 <b>{translate("Payment log")}:</b>\n']
        for user_id, paid_at, for_friend in entries:
            name = db.compose_full_name(user_id)
            time_str = paid_at.strftime('%H:%M') if isinstance(paid_at, datetime.datetime) else str(paid_at)[:5]
            note = f' ({translate("probably for friend")})' if for_friend else f' ({translate("probably for self")})'
            lines.append(f'• <b>{name}</b> {translate("marked payment at")} {time_str}{note}')
        await update.message.reply_text('\n'.join(lines), parse_mode=ParseMode.HTML)


@logger.catch
@make_translatable_user_id_context
# Removed legacy Maxwell linking functions


@logger.catch
@make_translatable_user_id_context
async def show_help(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    new_chat_id_memoization(update.message.chat_id, update.message.from_user.language_code)
    event_text = translate("""
Available BOT commands:

/event TEXT
Register new event

/event_remove
Remove open event

/event_update TEXT
Change event description

/limit XX
Set players limit

/event_datetime DATE TIME
Set event date and time in any format. It will parsed automatically.
Example 1: 2023-01-30, 18:00
Example2: tomorrow, 14:30

/info
Show event details

/add
Register yourself to the event

/remove
Revoke your application

/add_leg
Register another player (not participates in this chat) to the event

/rem_leg
Revoke register for another player

/pay
Confirm payment for the event

/payments
Show payment log for the current event

/blik PHONE
Set BLIK phone number for the current event

/lang
Change bot language settings

/fix
Fix event statistics (increment participants counters)

/penalty USERID
Increase someone's PENALTY counter for unreasonable skipping of the event without notification others.
You can find USERID by command /stat

/stat
This group members statistics (registrations and penalties)

# Removed legacy /link and /unlink help text
""")
    await context.bot.send_message(update.message.chat_id, event_text, parse_mode=ParseMode.HTML)

@logger.catch
@make_translatable_user_id_context
async def set_language(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    keyboard = [
        [InlineKeyboardButton("Русский 🇷🇺", callback_data='SET_LANG_ru')],
        [InlineKeyboardButton("Українська 🇺🇦", callback_data='SET_LANG_uk')],
        [InlineKeyboardButton("Português 🇵🇹", callback_data='SET_LANG_pt')],
        [InlineKeyboardButton("العربية 🇸🇦", callback_data='SET_LANG_ar')],
        [InlineKeyboardButton("English 🇬🇧", callback_data='SET_LANG_en')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(translate("Choose your language:"), reply_markup=reply_markup)

@logger.catch
@make_translatable_user_id_context
async def set_blik(update, context):
    if not update.message:
        return
    translate = context.user_data['translate']
    this_chat_id = update.message.chat_id
    phone = parse_cmd_arg(update, context)
    if not phone:
        await update.message.reply_text(translate("Usage: /blik PHONE"))
        return
    if not db.get_event_text(this_chat_id):
        await update.message.reply_text(translate("No active event found."))
        return
    db.set_event_blik_phone(this_chat_id, phone)
    await update.message.reply_text(f"BLIK: {phone}")
    await show_info(update, context)

@logger.catch
@make_translatable_user_id_context
async def unknown_command_handler(update, context):
    translate = context.user_data['translate']
    if not update.message:
        logger.warning("No message in update handler.")
        return
    this_chat_id = update.message.chat_id
    if update.message.new_chat_members:
        await show_info(update, context)
    text = (update.message.text or "").strip()
    if not text:
        return
    new_chat_id_memoization(this_chat_id, update.message.from_user.language_code)
    # Логируем только действительно неизвестные команды (начинающиеся с /)
    if text.startswith('/'):
        logger.info(f'Unknown command typed: {text}')

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu

async def shutdown(application, loop):
    logger.info("Shutting down bot...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def health_check_handler(reader, writer):
    """Simple HTTP health-check responder"""
    data = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"
    writer.write(data)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def main():
    logger.remove()
    logger.add(os.path.join(BOT_DIR, "logs", "logs.log"), level="INFO")
    logger.add(sys.stderr, level="WARNING")

    # Try environment variable first, then fall back to token.txt
    api_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not api_token:
        try:
            with open(os.path.join(BOT_DIR, 'token.txt'), encoding='utf-8') as f:
                api_token = f.readline().strip()
        except Exception as err:
            logger.exception(err)
            print("Set TELEGRAM_BOT_TOKEN env variable or create token.txt")
            sys.exit(1)
    if not api_token:
        print("TELEGRAM_BOT_TOKEN is empty")
        sys.exit(1)

    # Configure proxy if set (for regions where Telegram is blocked)
    proxy_url = os.getenv('TELEGRAM_PROXY')
    builder = Application.builder().token(api_token)
    if proxy_url:
        logger.info(f"Using proxy: {proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url}")
        builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)
    application = builder.build()

    # Initialize database tables and run migrations
    db.init_database()

    # Start health-check server (background)
    port = int(os.getenv("PORT", "10000"))
    try:
        health_server = await asyncio.start_server(health_check_handler, '0.0.0.0', port)
        logger.info(f"Health-check server started on port {port}")
        # Keep the server running in the background
        asyncio.create_task(health_server.serve_forever())
    except Exception as e:
        logger.warning(f"Could not start health-check server on port {port}: {e}")

    # Load known chat IDs
    global KNOWN_CHAT_IDS
    KNOWN_CHAT_IDS = db.get_all_chat_ids()

    # Добавление обработчиков команд
    application.add_handler(CommandHandler('add', add_player))
    application.add_handler(CommandHandler('remove', remove_player))
    application.add_handler(CommandHandler('add_leg', add_legioneer))
    application.add_handler(CommandHandler('rem_leg', remove_legioneer))
    application.add_handler(CommandHandler('info', show_info))
    application.add_handler(CommandHandler('help', show_help))
    application.add_handler(CommandHandler('stat', show_stat))
    application.add_handler(CommandHandler('fix', fix_squad))
    application.add_handler(CommandHandler('event', create_new_event))
    application.add_handler(CommandHandler('event_remove', remove_all_chat_events))
    application.add_handler(CommandHandler('event_update', update_event))
    application.add_handler(CommandHandler('limit', set_players_limit))
    application.add_handler(CommandHandler('penalty', penalty_player))
    application.add_handler(CommandHandler('event_datetime', set_event_datetime))
    application.add_handler(CommandHandler('pay', confirm_payment))
    application.add_handler(CommandHandler('payments', show_payments))
    application.add_handler(CommandHandler('blik', set_blik))
    application.add_handler(CommandHandler('lang', set_language))
    application.add_handler(CommandHandler('set_log_topic', set_log_topic))
    application.add_handler(CommandHandler('set_logs_topic', set_log_topic))
    application.add_handler(CommandHandler('set_lists_topic', set_lists_topic))
    application.add_handler(MessageHandler(filters.StatusUpdate.FORUM_TOPIC_CREATED, forum_topic_created_handler))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT | filters.StatusUpdate.NEW_CHAT_MEMBERS, unknown_command_handler))

    logger.info("Telegram Futsal Bot is starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Bot is running...")

    # Создаём событие для ожидания
    stop_event = asyncio.Event()

    # Настройка обработки сигналов
    loop = asyncio.get_running_loop()
    def signal_handler():
        logger.info("Received shutdown signal (Ctrl+C or SIGTERM)")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        logger.info("Main task was cancelled, initiating shutdown...")

    await shutdown(application, loop)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close