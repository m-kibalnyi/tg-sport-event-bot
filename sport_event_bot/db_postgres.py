# -*- coding: utf-8 -*-
"""Backward compatibility layer for db_postgres module."""

# Fix imports to support both direct run and module run
try:
    from sport_event_bot.db.base import PLATFORM, _exec, _exec_many, reconnect  # noqa: F401
    from sport_event_bot.db.chats import (  # noqa: F401
        get_all_chat_ids,
        get_chat_lang,
        get_latest_bot_message_id,
        get_latest_bot_message_text,
        get_lists_thread_id,
        get_log_thread_id,
        register_new_chat_id,
        save_latest_bot_message,
        set_chat_lang,
        set_lists_thread_id,
        set_log_thread_id,
    )
    from sport_event_bot.db.events import (  # noqa: F401
        close_all_open_events_for_chat,
        event,
        fix_event,
        get_event_blik_phone,
        get_event_creator,
        get_event_datetime,
        get_event_extra1,
        get_event_id_by_chat_id,
        get_event_limit,
        get_event_location,
        get_event_payment_url,
        get_event_telegraph_url,
        get_event_text,
        set_event_blik_phone,
        set_event_datetime,
        set_event_extra1,
        set_event_payment_url,
        set_event_telegraph_url,
        set_players_limit,
        update_event_text,
    )
    from sport_event_bot.db.init import init_database  # noqa: F401
    from sport_event_bot.db.logs import add_event_log, get_event_logs, prune_old_event_logs  # noqa: F401
    from sport_event_bot.db.participants import (  # noqa: F401
        apply_for_legioneer,
        apply_for_participation_in_the_event,
        apply_for_thinking,
        get_event_revoked_users,
        get_event_users,
        get_legioneer_user,
        get_only_chat_participants,
        get_thinking_users,
        revoke_all_user_legioneers,
        revoke_application_for_the_event,
        revoke_for_legioneer,
    )
    from sport_event_bot.db.payments import (  # noqa: F401
        get_payment_log,
        get_payment_status,
        process_payment,
        set_payment_status,
    )
    from sport_event_bot.db.penalties import (  # noqa: F401
        get_active_penalties,
        get_chat_user_rp,
        get_user_cancellation_datetime,
        penalty_for_user_in_chat,
    )
    from sport_event_bot.db.users import (  # noqa: F401
        add_or_update_user,
        compose_full_name,
        get_all_userids,
        get_user_lang,
        set_user_lang,
    )
except (ImportError, ValueError):
    pass
