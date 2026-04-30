import datetime
import html

from loguru import logger

import sport_event_bot.db_postgres as db
from sport_event_bot.utils.helpers import parse_datetime

LOCATION_HIDE_MARKER = "null"


def create_event_full_text(chat_id: int, translate, lang: str = "ru") -> str:
    """Renders the entire event message text."""
    try:
        event_name = db.get_event_text(chat_id)
        logger.info(f"Rendering event for chat_id={chat_id}, event_name={event_name}")
        if not event_name:
            logger.warning(f"No active event found for chat_id={chat_id}")
            return translate("No active event.")

        limit = db.get_event_limit(chat_id)
        dt_str = db.get_event_datetime(chat_id)
        location = db.get_event_location(chat_id)
        payment_url = db.get_event_payment_url(chat_id)
        telegraph_url = db.get_event_telegraph_url(chat_id)
        blik_phone = db.get_event_blik_phone(chat_id)

        import os

        web_url = os.getenv("PAYMENTS_PAGE_URL")
        event_id = db.get_event_id_by_chat_id(chat_id)

        logger.info(
            f"Event details: id={event_id}, limit={limit}, dt={dt_str}, loc={location}, pay={payment_url}, "
            f"tph={telegraph_url}, blik={blik_phone}, web={web_url}"
        )

        # Datetime parsing for time left
        dt = None
        if dt_str:
            try:
                dt = parse_datetime(dt_str, lang)
            except Exception as e:
                logger.error(f"Failed to parse datetime '{dt_str}': {e}")

        time_left_str = ""
        if dt:
            now = datetime.datetime.now()
            if dt > now:
                diff = dt - now
                days = diff.days
                hours = diff.seconds // 3600
                time_left_str = f"\n⏳ {translate('Time left')}: {days} {translate('days')} {translate('and')} {hours} {translate('hours')}"  # noqa: E501
            else:
                time_left_str = f"\n⌛ {translate('Event time out')}"

        header = f'🎉"<b>{html.escape(event_name)}</b>"🎉\n'
        header += f"{translate('Players limit')}: {limit}\n"
        header += f"📅 {translate('Event date and time')}: {dt_str}{time_left_str}\n"

        if location and location.lower() != LOCATION_HIDE_MARKER:
            header += f"\n📍 <b>{html.escape(location)}</b>\n"
            header += f"🔗 <a href='https://maps.google.com'>{translate('Location map')}</a>\n"

        # Primary Payment/Info link
        main_link_added = False
        if web_url:
            u = web_url
            if "payments.php" in u:
                u = u.replace("payments.php", "event.php")
            elif "event.php" not in u:
                if not any(ext in u for ext in [".php", ".html"]):
                    u = u.rstrip("/") + "/event.php"

            if event_id:
                if "localhost" in u:
                    u = u.replace("https://localhost", "http://localhost")

                main_link_added = True

        if not main_link_added:
            if payment_url:
                main_link_added = True
            elif telegraph_url:
                header += f'📝 <a href="{telegraph_url}"><b>{translate("Current payments")}</b></a>\n'
                main_link_added = True

        if blik_phone:
            header += f"📲 BLIK: <code>{blik_phone}</code>\n"

        # Web shorthand links
        if web_url:
            base_url = web_url
            for suffix in ["payments.php", "event.php"]:
                if suffix in base_url:
                    base_url = base_url.split(suffix)[0]
            base_url = base_url.rstrip("/")
            if "localhost" in base_url:
                base_url = base_url.replace("https://localhost", "http://localhost")

            links = []
            if event_id:
                links.append(f'<a href="{base_url}/event.php?event={event_id}">{translate("Event")}</a>')
                links.append(f'<a href="{base_url}/statistics.php?chat={chat_id}">{translate("Statistics")}</a>')
                links.append(f'<a href="{base_url}/event_logs.php?event={event_id}">{translate("Logs")}</a>')
            else:
                links.append(f'<a href="{base_url}/event.php">{translate("Event")}</a>')
                links.append(f'<a href="{base_url}/statistics.php?chat={chat_id}">{translate("Statistics")}</a>')
                links.append(f'<a href="{base_url}/event_logs.php">{translate("Logs")}</a>')
            header += f"🔗 {' | '.join(links)}\n"

        # Participants
        extra1 = db.get_event_extra1(chat_id)
        teams_data = None
        if extra1:
            try:
                import json

                teams_data = json.loads(extra1)
            except Exception as e:
                logger.warning(f"Failed to parse extra1: {e}")

        list_str = ""
        leg_count = 0 # Sequential legioneer counter
        
        if teams_data and "teams" in teams_data:
            list_str += f"\n{translate('Shuffled teams')}:\n"
            teams = teams_data["teams"]
            for team_name, team_players in teams.items():
                list_str += f"\n<b>{html.escape(team_name)}:</b>\n"
                if not team_players:
                    list_str += f"<i>{translate('Empty')}</i>\n"
                else:
                    for j, uid_data in enumerate(team_players):
                        uid = uid_data[0] if isinstance(uid_data, (list, tuple)) else uid_data
                        invited_by = uid_data[1] if isinstance(uid_data, (list, tuple)) and len(uid_data) > 1 else None

                        if 10 <= uid < 1010:
                            name = f"{translate('Legioner')} {uid - 9}"
                        else:
                            name = html.escape(db.compose_full_name(uid))

                        if invited_by and 10 <= uid < 1010:
                            inviter_name = html.escape(db.compose_full_name(invited_by))
                            name += f" ({translate('from')} {inviter_name})"
                        list_str += f"{j + 1}. {name}\n"

            reserve = teams_data.get("reserve", [])
            if reserve:
                list_str += f"\n--- {translate('RESERVE')} ---\n"
                for j, uid_data in enumerate(reserve):
                    uid = uid_data[0] if isinstance(uid_data, (list, tuple)) else uid_data
                    invited_by = uid_data[1] if isinstance(uid_data, (list, tuple)) and len(uid_data) > 1 else None

                    if 10 <= uid < 1010:
                        name = f"{translate('Legioner')} {uid - 9}"
                    else:
                        name = html.escape(db.compose_full_name(uid))

                    if invited_by and 10 <= uid < 1010:
                        inviter_name = html.escape(db.compose_full_name(invited_by))
                        name += f" ({translate('from')} {inviter_name})"
                    list_str += f"{j + 1}. {name}\n"
        else:
            players = db.get_event_users(chat_id)
            list_str = f"\n{translate('Players list')}:\n"
            if not players:
                list_str += f"<i>{translate('No applications yet')}</i>\n"
            else:
                for i, uid_data in enumerate(players):
                    uid, invited_by = uid_data if isinstance(uid_data, (list, tuple)) else (uid_data, None)

                    if i == limit and limit > 0:
                        list_str += f"\n--- {translate('RESERVE')} ---\n"
                    
                    if 10 <= uid < 1010:
                        name = f"{translate('Legioner')} {uid - 9}"
                        paid_mark = "➕"
                    else:
                        name = html.escape(db.compose_full_name(uid))
                        paid_mark = "✅"

                    if db.get_payment_status(chat_id, uid):
                        paid_mark = "💰"

                    if invited_by and 10 <= uid < 1010:
                        inviter_name = html.escape(db.compose_full_name(invited_by))
                        name += f" ({translate('from')} {inviter_name})"

                    list_str += f"{i + 1}. {paid_mark} {name}\n"

        thinking = db.get_thinking_users(chat_id)
        if thinking:
            list_str += f"\n=====================\n\n{translate('Thinking')}:\n"
            for i, uid in enumerate(thinking):
                if 10 <= uid < 1010:
                    name = f"{translate('Legioner')} {uid - 9}"
                else:
                    name = html.escape(db.compose_full_name(uid))
                list_str += f"{i + 1}. 🤔 {name}\n"

        revoked = db.get_event_revoked_users(chat_id)
        if revoked:
            list_str += f"\n=====================\n\n{translate('I am not going')}:\n"
            for i, uid in enumerate(revoked):
                if 10 <= uid < 1010:
                    name = f"{translate('Legioner')} {uid - 9}"
                else:
                    name = html.escape(db.compose_full_name(uid))
                list_str += f"{i + 1}. ❌ {name}\n"

        penalties = db.get_active_penalties(chat_id)
        if penalties:
            list_str += f"\n=====================\n\n{translate('Yellow Cards')} 🟨:\n"
            for i, (name, expr) in enumerate(penalties):
                list_str += f"{i + 1}. 🟨 {html.escape(name)} ({translate('expires in')} {expr})\n"

        return header + list_str
    except Exception as e:
        logger.exception(e)
        return f"Error rendering event: {e}"
