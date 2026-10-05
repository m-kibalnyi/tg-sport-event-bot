from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import ConversationHandler

from sport_event_bot.handlers.event_conv import (
    EVENT_SET_LIMIT,
    EVENT_SET_NAME,
    create_new_event,
    event_name_handler,
    finalize_event_creation,
)


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_conv.db")
@patch("sport_event_bot.handlers.event_conv.is_user_admin")
@patch("sport_event_bot.handlers.event_conv.parse_cmd_arg")
async def test_create_new_event_start(mock_parse_arg, mock_admin, mock_db, mock_update, mock_context, translate):
    # Setup
    mock_admin.return_value = True
    mock_context.user_data["translate"] = translate
    mock_db.get_event_text.return_value = None
    mock_parse_arg.return_value = ""

    mock_update.message.reply_text = AsyncMock()

    # Execute
    result = await create_new_event(mock_update, mock_context)

    # Verify: suggests default event name with confirm/change
    assert result == EVENT_SET_NAME
    assert mock_context.user_data["new_event_data"]["name"] == "Среда, Величка, сбор 20:00, начало 20:15"
    mock_update.message.reply_text.assert_called_once()
    assert "Среда, Величка, сбор 20:00, начало 20:15" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_conv.db")
@patch("sport_event_bot.handlers.event_conv.is_user_admin")
@patch("sport_event_bot.handlers.event_conv.parse_cmd_arg")
async def test_create_new_event_allows_when_previous_exists(
    mock_parse_arg, mock_admin, mock_db, mock_update, mock_context, translate
):
    # Setup - an active event already exists, but we allow creating new event
    mock_admin.return_value = True
    mock_context.user_data["translate"] = translate
    mock_db.get_event_text.return_value = "Old Active Event"
    mock_parse_arg.return_value = "New Wednesday Match"

    mock_update.message.reply_text = AsyncMock()

    # Execute
    result = await create_new_event(mock_update, mock_context)

    # Verify: does not error, proceeds to next step
    assert result == EVENT_SET_LIMIT
    assert mock_context.user_data["new_event_data"]["name"] == "New Wednesday Match"


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_conv.db")
@patch("sport_event_bot.handlers.event_conv.is_user_admin")
@patch("sport_event_bot.handlers.event_conv.parse_cmd_arg")
@patch("sport_event_bot.handlers.event_conv.finalize_event_creation", new_callable=AsyncMock)
async def test_create_new_event_json_one_shot(
    mock_finalize, mock_parse_arg, mock_admin, mock_db, mock_update, mock_context, translate
):
    mock_admin.return_value = True
    mock_context.user_data["translate"] = translate
    mock_parse_arg.return_value = (
        '{"name": "Inline Football", "limit": 14, "dt": "2026-10-07 20:15", "location": "https://maps.google.com/test"}'
    )
    mock_finalize.return_value = ConversationHandler.END

    result = await create_new_event(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_finalize.assert_called_once()
    assert mock_context.user_data["new_event_data"]["name"] == "Inline Football"
    assert mock_context.user_data["new_event_data"]["limit"] == 14
    assert mock_context.user_data["new_event_data"]["location"] == "https://maps.google.com/test"


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_conv.db")
@patch("sport_event_bot.handlers.event_conv.is_user_admin")
@patch("sport_event_bot.handlers.event_conv.parse_cmd_arg")
@patch("sport_event_bot.handlers.event_conv.finalize_event_creation", new_callable=AsyncMock)
async def test_create_new_event_user_exact_command(
    mock_finalize, mock_parse_arg, mock_admin, mock_db, mock_update, mock_context, translate
):
    mock_admin.return_value = True
    mock_context.user_data["translate"] = translate
    user_cmd = '{"name":"🎉 Среда 07.10 Orlik Wieliczka Начало 20:15 (сбор 20:00)🎉","limit":21,"datetime":"2026-10-07 20:15","location":"https://maps.app.goo.gl/ZWY7bQzLruA3qnMM7?g_st=ic","free":false,"blik":"791162031"}'
    mock_parse_arg.return_value = user_cmd
    mock_finalize.return_value = ConversationHandler.END

    result = await create_new_event(mock_update, mock_context)

    assert result == ConversationHandler.END
    mock_finalize.assert_called_once()
    data = mock_context.user_data["new_event_data"]
    assert data["name"] == "🎉 Среда 07.10 Orlik Wieliczka Начало 20:15 (сбор 20:00)🎉"
    assert data["limit"] == 21
    assert data["datetime"] == "2026-10-07 20:15"
    assert data["location"] == "https://maps.app.goo.gl/ZWY7bQzLruA3qnMM7?g_st=ic"
    assert data["free"] is False
    assert data["blik"] == "791162031"


@pytest.mark.asyncio
async def test_event_name_handler(mock_update, mock_context, translate):
    # Setup
    mock_context.user_data["translate"] = translate
    mock_context.user_data["new_event_data"] = {}
    mock_update.message.text = "New Match Name"

    # We need to mock event_ask_step since it's called by event_name_handler
    with patch("sport_event_bot.handlers.event_conv.event_ask_step", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = EVENT_SET_LIMIT

        # Execute
        result = await event_name_handler(mock_update, mock_context)

        # Verify
        assert result == EVENT_SET_LIMIT
        assert mock_context.user_data["new_event_data"]["name"] == "New Match Name"


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_conv.db")
@patch("sport_event_bot.handlers.event_conv.is_user_admin")
@patch("sport_event_bot.handlers.event_conv.create_event_full_text")
@patch("sport_event_bot.handlers.event_conv.build_message_markup")
@patch("sport_event_bot.handlers.event_conv.log_event", new_callable=AsyncMock)
async def test_finalize_event_creation(
    mock_log, mock_markup, mock_render, mock_admin, mock_db, mock_update, mock_context, translate
):
    # Setup
    mock_admin.return_value = True
    mock_context.user_data["translate"] = translate
    mock_context.user_data["new_event_data"] = {"name": "Test Event", "limit": 16, "datetime": "2024-12-01 12:00"}

    # Mock bot methods
    mock_context.bot.send_message = AsyncMock(return_value=MagicMock(message_id=777))
    mock_context.bot.edit_message_text = AsyncMock()

    mock_db.get_lists_thread_id.return_value = None
    mock_db.event = MagicMock()
    mock_db.get_event_id_by_chat_id.return_value = 123
    mock_render.return_value = "Full Event Text"

    mock_update.callback_query = None
    mock_update.message.reply_text = AsyncMock()

    # Execute
    result = await finalize_event_creation(mock_update, mock_context)

    # Verify
    assert result == ConversationHandler.END
    mock_db.event.assert_called_once()
    assert mock_db.event.call_args[0][1] == "Test Event"
    assert mock_db.event.call_args[0][3] == 16

    mock_context.bot.edit_message_text.assert_called_once()
    assert "Full Event Text" in mock_context.bot.edit_message_text.call_args[1]["text"]
    mock_log.assert_called_once()
