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
@patch("sport_event_bot.handlers.event_conv.parse_cmd_arg")
async def test_create_new_event_start(mock_parse_arg, mock_db, mock_update, mock_context, translate):
    # Setup
    mock_context.user_data["translate"] = translate
    mock_db.get_event_text.return_value = None
    mock_parse_arg.return_value = ""

    mock_update.message.reply_text = AsyncMock()

    # Execute
    result = await create_new_event(mock_update, mock_context)

    # Verify
    assert result == EVENT_SET_NAME
    mock_update.message.reply_text.assert_called_once()
    assert "What is the name of the event?" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_conv.db")
async def test_create_new_event_already_exists(mock_db, mock_update, mock_context, translate):
    # Setup
    mock_context.user_data["translate"] = translate
    mock_db.get_event_text.return_value = "Existing Event"

    mock_update.message.reply_text = AsyncMock()

    # Execute
    result = await create_new_event(mock_update, mock_context)

    # Verify
    assert result == ConversationHandler.END
    mock_update.message.reply_text.assert_called_once_with("Error: An active event already exists.")


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
@patch("sport_event_bot.handlers.event_conv.create_event_full_text")
@patch("sport_event_bot.handlers.event_conv.build_message_markup")
@patch("sport_event_bot.handlers.event_conv.log_event", new_callable=AsyncMock)
async def test_finalize_event_creation(
    mock_log, mock_markup, mock_render, mock_db, mock_update, mock_context, translate
):
    # Setup
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
