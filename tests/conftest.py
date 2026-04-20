from unittest.mock import MagicMock

import pytest


@pytest.fixture
def translate():
    """Mock translation function that returns the text as-is."""
    return lambda t: t


@pytest.fixture
def mock_update():
    """Create a basic mock Telegram Update."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.full_name = "Test User"
    update.effective_chat.id = -100123456789
    update.message.chat_id = -100123456789
    update.message.text = "Test Message"
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Create a basic mock Telegram CallbackContext."""
    context = MagicMock()
    context.user_data = {}
    context.bot.send_message = MagicMock()
    context.bot.edit_message_text = MagicMock()
    return context
