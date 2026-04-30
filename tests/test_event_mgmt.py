import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sport_event_bot.handlers.event_mgmt import show_info

@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_mgmt.db")
@patch("sport_event_bot.handlers.event_mgmt.is_user_admin")
@patch("sport_event_bot.handlers.event_mgmt.create_event_full_text")
@patch("sport_event_bot.handlers.event_mgmt.build_message_markup")
async def test_show_info_no_event(mock_markup, mock_render, mock_admin, mock_db, mock_update, mock_context, translate):
    # Setup
    mock_context.user_data["translate"] = translate
    mock_db.get_event_text.return_value = None
    mock_update.effective_chat.id = 123
    mock_update.message.reply_text = AsyncMock()
    mock_db.get_lists_thread_id.return_value = None

    # Execute
    await show_info(mock_update, mock_context)

    # Verify
    mock_db.get_event_text.assert_called_once_with(123)
    mock_render.assert_not_called()
    mock_markup.assert_not_called()
    
    # Check that reply_text was called with no markup
    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    assert args[0] == "No active event."
    assert kwargs.get("reply_markup") is None

@pytest.mark.asyncio
@patch("sport_event_bot.handlers.event_mgmt.db")
@patch("sport_event_bot.handlers.event_mgmt.is_user_admin")
@patch("sport_event_bot.handlers.event_mgmt.create_event_full_text")
@patch("sport_event_bot.handlers.event_mgmt.build_message_markup")
async def test_show_info_with_event(mock_markup, mock_render, mock_admin, mock_db, mock_update, mock_context, translate):
    # Setup
    mock_context.user_data["translate"] = translate
    mock_db.get_event_text.return_value = "Sunday Football"
    mock_update.effective_chat.id = 123
    mock_update.message.reply_text = AsyncMock()
    mock_admin.return_value = True
    mock_db.get_event_blik_phone.return_value = "123456789"
    mock_db.get_event_extra1.return_value = "{}"
    mock_render.return_value = "Full Event Details"
    mock_markup.return_value = MagicMock()
    mock_db.get_lists_thread_id.return_value = None

    # Execute
    await show_info(mock_update, mock_context)

    # Verify
    mock_db.get_event_text.assert_called_once_with(123)
    mock_render.assert_called_once()
    mock_markup.assert_called_once()
    
    # Check that reply_text was called with markup
    mock_update.message.reply_text.assert_called_once()
    args, kwargs = mock_update.message.reply_text.call_args
    assert args[0] == "Full Event Details"
    assert kwargs.get("reply_markup") is not None
