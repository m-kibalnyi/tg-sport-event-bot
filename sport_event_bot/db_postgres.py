# -*- coding: utf-8 -*-
"""Backward compatibility layer for db_postgres module."""
# Fix imports to support both direct run and module run
try:
    from sport_event_bot.db.base import PLATFORM, reconnect, _exec, _exec_many
    from sport_event_bot.db.init import init_database
    from sport_event_bot.db.users import (
        add_or_update_user, compose_full_name, get_all_userids,
        get_user_lang, set_user_lang
    )
    from sport_event_bot.db.chats import (
        register_new_chat_id, get_all_chat_ids, get_chat_lang, set_chat_lang,
        get_latest_bot_message_id, get_latest_bot_message_text, save_latest_bot_message,
        get_log_thread_id, set_log_thread_id, get_lists_thread_id, set_lists_thread_id
    )
    from sport_event_bot.db.events import (
        event, update_event_text, get_event_text, set_players_limit, get_event_limit,
        set_event_datetime, get_event_datetime, get_event_location, get_event_payment_url,
        set_event_payment_url, get_event_extra1, set_event_extra1, get_event_telegraph_url,
        set_event_telegraph_url, fix_event, close_all_open_events_for_chat,
        get_event_id_by_chat_id, get_event_creator, get_event_blik_phone, set_event_blik_phone
    )
    from sport_event_bot.db.participants import (
        get_event_users, get_event_revoked_users, get_thinking_users,
        apply_for_participation_in_the_event, revoke_application_for_the_event,
        apply_for_thinking, get_legioneer_user, apply_for_legioneer,
        revoke_for_legioneer, revoke_all_user_legioneers, get_only_chat_participants
    )
    from sport_event_bot.db.payments import set_payment_status, get_payment_status, process_payment, get_payment_log
    from sport_event_bot.db.penalties import (
        penalty_for_user_in_chat, get_chat_user_rp, get_active_penalties,
        get_user_cancellation_datetime
    )
    from sport_event_bot.db.logs import add_event_log, get_event_logs, prune_old_event_logs
except (ImportError, ValueError):
    from db.base import PLATFORM, reconnect, _exec, _exec_many
    from db.init import init_database
    from db.users import (
        add_or_update_user, compose_full_name, get_all_userids,
        get_user_lang, set_user_lang
    )
    from db.chats import (
        register_new_chat_id, get_all_chat_ids, get_chat_lang, set_chat_lang,
        get_latest_bot_message_id, get_latest_bot_message_text, save_latest_bot_message,
        get_log_thread_id, set_log_thread_id, get_lists_thread_id, set_lists_thread_id
    )
    from db.events import (
        event, update_event_text, get_event_text, set_players_limit, get_event_limit,
        set_event_datetime, get_event_datetime, get_event_location, get_event_payment_url,
        set_event_payment_url, get_event_extra1, set_event_extra1, get_event_telegraph_url,
        set_event_telegraph_url, fix_event, close_all_open_events_for_chat,
        get_event_id_by_chat_id, get_event_creator, get_event_blik_phone, set_event_blik_phone
    )
    from db.participants import (
        get_event_users, get_event_revoked_users, get_thinking_users,
        apply_for_participation_in_the_event, revoke_application_for_the_event,
        apply_for_thinking, get_legioneer_user, apply_for_legioneer,
        revoke_for_legioneer, revoke_all_user_legioneers, get_only_chat_participants
    )
    from db.payments import set_payment_status, get_payment_status, process_payment, get_payment_log
    from db.penalties import (
        penalty_for_user_in_chat, get_chat_user_rp, get_active_penalties,
        get_user_cancellation_datetime
    )
    from db.logs import add_event_log, get_event_logs, prune_old_event_logs
