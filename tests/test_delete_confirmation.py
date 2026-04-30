import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from telegram import Update, CallbackQuery, Message, User, Chat
from sport_event_bot.handlers.callback import button

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.callback_query = MagicMock(spec=CallbackQuery)
    update.callback_query.message = MagicMock(spec=Message)
    update.callback_query.from_user = MagicMock(spec=User)
    update.callback_query.from_user.id = 123
    update.callback_query.from_user.first_name = "Admin"
    update.callback_query.message.chat_id = 456
    update.callback_query.message.message_id = 789
    update.effective_user.id = 123
    update.effective_chat.id = 456
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.user_data = {"translate": lambda t: t, "lang": "en"}
    return context

@pytest.mark.asyncio
@patch("sport_event_bot.handlers.callback.db")
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.callback.is_user_admin")
@patch("sport_event_bot.handlers.callback.create_event_full_text")
@patch("sport_event_bot.handlers.callback.build_message_markup")
@patch("sport_event_bot.handlers.callback.build_confirmation_markup")
async def test_delete_event_request(mock_conf_markup, mock_msg_markup, mock_render, mock_is_admin, mock_loc_db, mock_db, mock_update, mock_context):
    # Setup
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_is_admin.return_value = True
    mock_update.callback_query.data = "DELETE_EVENT"
    
    # Execute
    await button(mock_update, mock_context)
    
    # Verify
    mock_update.callback_query.edit_message_text.assert_called_once()
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    assert "Are you sure" in kwargs["text"]
    assert kwargs["reply_markup"] == mock_conf_markup.return_value

@pytest.mark.asyncio
@patch("sport_event_bot.handlers.callback.db")
@patch("sport_event_bot.utils.localization.db")
@patch("sport_event_bot.handlers.callback.is_user_admin")
@patch("sport_event_bot.handlers.callback.create_event_full_text")
@patch("sport_event_bot.handlers.callback.build_message_markup")
async def test_confirm_delete_event(mock_msg_markup, mock_render, mock_is_admin, mock_loc_db, mock_db, mock_update, mock_context):
    # Setup
    mock_loc_db.get_user_lang.return_value = "en"
    mock_loc_db.get_chat_lang.return_value = "en"
    mock_is_admin.return_value = True
    mock_update.callback_query.data = "CONFIRM_DELETE_EVENT"
    mock_db.get_event_text.return_value = None # Event deleted
    
    # Execute
    await button(mock_update, mock_context)
    
    # Verify
    mock_db.close_all_open_events_for_chat.assert_called_once_with(456)
    mock_update.callback_query.answer.assert_called_with("All open events for this chat were closed.")
    
    # Verify UI refresh (no event state)
    mock_update.callback_query.edit_message_text.assert_called_once()
    args, kwargs = mock_update.callback_query.edit_message_text.call_args
    assert "No active event" in kwargs["text"]
    assert kwargs["reply_markup"] is None
