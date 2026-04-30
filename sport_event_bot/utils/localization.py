# -*- coding: utf-8 -*-
import functools
import gettext
import os

import sport_event_bot.db_postgres as db

BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALE_DIR = os.path.join(BOT_DIR, "locale")

TRANSLATIONS = {
    "uk": gettext.translation("ua", localedir=LOCALE_DIR, languages=["uk"], fallback=True).gettext,
    "ru": gettext.translation("ru", localedir=LOCALE_DIR, languages=["ru"], fallback=True).gettext,
    "pl": gettext.translation("pl", localedir=LOCALE_DIR, languages=["pl"], fallback=True).gettext,
    "en": gettext.translation("en", localedir=LOCALE_DIR, languages=["en"], fallback=True).gettext,
}


def make_translatable_user_id_context(func):
    """Decorator to inject 'translate' function into context.user_data based on user preference."""

    @functools.wraps(func)
    async def wrapper(update, context):
        if not update.effective_user:
            return await func(update, context)

        user_id = update.effective_user.id
        # Try user language, then chat language, then default
        lang = db.get_user_lang(user_id) or db.get_chat_lang(update.effective_chat.id) or "ru"

        context.user_data["lang"] = lang
        context.user_data["translate"] = TRANSLATIONS.get(lang, lambda t: t)
        return await func(update, context)

    return wrapper
