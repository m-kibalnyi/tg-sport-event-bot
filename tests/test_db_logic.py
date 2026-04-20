import datetime
from unittest.mock import MagicMock, patch

# We need to mock 'reconnect' and '_exec' in the module being tested
import sport_event_bot.db.events as events_db


@patch("sport_event_bot.db.events.reconnect")
@patch("sport_event_bot.db.events._exec")
@patch("sport_event_bot.db.events.register_new_chat_id")
def test_db_create_event_sql(mock_register, mock_exec, mock_reconnect):
    # Setup
    mock_conn = MagicMock()
    mock_reconnect.return_value = mock_conn

    chat_id = 123
    description = "Monthly Match"
    dt = datetime.datetime(2024, 12, 1, 15, 0)
    limit = 16
    msg_id = 999
    full_text = "Header\nList"
    creator_id = 456
    location = "Main Court"

    # Execute
    events_db.event(chat_id, description, dt, limit, msg_id, full_text, creator_id, location)

    # Verify register_new_chat_id is called
    mock_register.assert_called_once_with(chat_id, "ru")

    # Verify _exec was called with the correct table and VALUES
    # We can check the second argument (query) and third argument (params)
    assert mock_exec.call_count == 1
    args, kwargs = mock_exec.call_args
    query = args[1]
    params = args[2]

    assert "INSERT INTO Events" in query
    assert description in params
    assert "2024-12-01 15:00" in params
    assert limit in params
    assert str(msg_id) in params
    assert creator_id in params
    assert location in params


@patch("sport_event_bot.db.events.reconnect")
@patch("sport_event_bot.db.events._exec")
def test_db_get_event_text(mock_exec, mock_reconnect):
    mock_conn = MagicMock()
    mock_reconnect.return_value = mock_conn

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("Original Match Name",)
    mock_exec.return_value = mock_cursor

    result = events_db.get_event_text(123)

    assert result == "Original Match Name"
    args, _ = mock_exec.call_args
    query = args[1]
    assert "SELECT description FROM Events" in query
    assert "status = 'Open'" in query
