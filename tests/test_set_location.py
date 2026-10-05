from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ParseMode

from sport_event_bot.handlers.admin import set_location


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_chat.id = 12345
    update.message = MagicMock()
    update.message.chat_id = 12345
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.user_data = {"translate": lambda t: t, "lang": "ru"}
    context.args = []
    context.bot = MagicMock()
    context.bot.edit_message_text = AsyncMock()
    return context


@pytest.mark.asyncio
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.admin.is_user_admin", new_callable=AsyncMock)
async def test_set_location_non_admin(mock_admin, mock_loc_db, mock_update, mock_context):
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_admin.return_value = False
    mock_context.args = ["https://maps.app.goo.gl/xyz"]

    await set_location(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with("Access denied: only admins can use this command.")


@pytest.mark.asyncio
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.admin.is_user_admin", new_callable=AsyncMock)
async def test_set_location_no_args(mock_admin, mock_loc_db, mock_update, mock_context):
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_admin.return_value = True
    mock_context.args = []

    await set_location(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(
        "Usage: /set_location <google maps URL or place name>"
    )


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.admin.db")
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.admin.is_user_admin", new_callable=AsyncMock)
async def test_set_location_no_active_event(mock_admin, mock_loc_db, mock_db, mock_update, mock_context):
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_admin.return_value = True
    mock_context.args = ["https://maps.app.goo.gl/xyz"]
    mock_db.get_event_text.return_value = None

    await set_location(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with("No active event found.")
    mock_db.set_event_location.assert_not_called()


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.admin.db")
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.admin.is_user_admin", new_callable=AsyncMock)
async def test_set_location_success_url(mock_admin, mock_loc_db, mock_db, mock_update, mock_context):
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_admin.return_value = True
    location_url = "https://maps.app.goo.gl/xyz"
    mock_context.args = [location_url]

    mock_db.get_event_text.return_value = "Wednesday Match"
    mock_db.get_latest_bot_message_id.return_value = "999"
    mock_db.get_event_blik_phone.return_value = "123456789"

    with patch("sport_event_bot.ui.render.create_event_full_text", return_value="Event full text with location"):
        await set_location(mock_update, mock_context)

    mock_db.set_event_location.assert_called_once_with(12345, location_url)
    mock_context.bot.edit_message_text.assert_called_once()
    edit_kwargs = mock_context.bot.edit_message_text.call_args[1]
    assert edit_kwargs["chat_id"] == 12345
    assert edit_kwargs["message_id"] == 999
    assert edit_kwargs["text"] == "Event full text with location"
    assert edit_kwargs["parse_mode"] == ParseMode.HTML

    mock_db.save_latest_bot_message.assert_called_once_with(12345, "999", "Event full text with location")
    mock_update.message.reply_text.assert_called_once_with("📍 Location updated for the current event.")


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.admin.db")
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.admin.is_user_admin", new_callable=AsyncMock)
async def test_set_location_success_text(mock_admin, mock_loc_db, mock_db, mock_update, mock_context):
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_admin.return_value = True
    mock_context.args = ["Wieliczka", "Arena", "Hall", "A"]

    mock_db.get_event_text.return_value = "Wednesday Match"
    mock_db.get_latest_bot_message_id.return_value = None

    with patch("sport_event_bot.ui.render.create_event_full_text", return_value="Updated Text"):
        await set_location(mock_update, mock_context)

    mock_db.set_event_location.assert_called_once_with(12345, "Wieliczka Arena Hall A")
    mock_context.bot.edit_message_text.assert_not_called()
    mock_update.message.reply_text.assert_called_once_with("📍 Location updated for the current event.")
