import pytest

from sport_event_bot.ui.render import create_event_full_text


@pytest.fixture
def mock_db(mocker):
    # Mocking the db_postgres module that is imported in render.py
    return mocker.patch("sport_event_bot.ui.render.db")


def test_create_event_full_text_no_event(mock_db):
    chat_id = 123
    mock_db.get_event_text.return_value = None

    def translate(t):
        return t

    result = create_event_full_text(chat_id, translate)
    assert result == "No active event."


def test_create_event_full_text_basic(mock_db, mocker):
    chat_id = 123
    mock_db.get_event_text.return_value = "Sunday Football"
    mock_db.get_event_limit.return_value = 14
    mock_db.get_event_datetime.return_value = "2024-12-01 12:00:00"
    mock_db.get_event_location.return_value = "Arena A"
    mock_db.get_event_payment_url.return_value = None
    mock_db.get_event_telegraph_url.return_value = None
    mock_db.get_event_blik_phone.return_value = "123456789"
    mock_db.get_event_id_by_chat_id.return_value = 1
    mock_db.get_event_extra1.return_value = None
    mock_db.get_event_users.return_value = [(100, None), (101, None)]
    mock_db.get_thinking_users.return_value = []
    mock_db.get_event_revoked_users.return_value = []
    mock_db.get_active_penalties.return_value = []

    mock_db.compose_full_name.side_effect = lambda uid: f"User_{uid}"
    mock_db.get_payment_status.return_value = False

    # Mock os.getenv for web_url
    mocker.patch("os.getenv", return_value="https://example.com")

    def translate(t):
        return t

    result = create_event_full_text(chat_id, translate)

    assert "Sunday Football" in result
    assert "Players limit: 14" in result
    assert "Arena A" in result
    assert "User_100" in result
    assert "User_101" in result
    assert "BLIK: <code>123456789</code>" in result


def test_create_event_full_text_with_teams(mock_db, mocker):
    chat_id = 123
    mock_db.get_event_text.return_value = "Team Match"
    mock_db.get_event_limit.return_value = 14
    mock_db.get_event_datetime.return_value = "2024-12-01 12:00:00"
    mock_db.get_event_location.return_value = "null"  # Hides location

    # Extra1 with teams JSON
    teams_json = '{"teams": {"Team A": [100, 101], "Team B": [102, 103]}, "reserve": [104]}'
    mock_db.get_event_extra1.return_value = teams_json

    mock_db.compose_full_name.side_effect = lambda uid: f"User_{uid}"

    mocker.patch("os.getenv", return_value=None)

    def translate(t):
        return t

    result = create_event_full_text(chat_id, translate)

    assert "Shuffled teams" in result
    assert "Team A" in result
    assert "Team B" in result
    assert "User_100" in result
    assert "User_104" in result
    assert "RESERVE" in result
    assert "Arena A" not in result  # because location is 'null'


def test_create_event_full_text_reserve_divider(mock_db, mocker):
    chat_id = 123
    mock_db.get_event_name.return_value = "Football"  # Wait, the code uses get_event_text
    mock_db.get_event_text.return_value = "Football"
    mock_db.get_event_limit.return_value = 2
    mock_db.get_event_datetime.return_value = "2024-12-01 12:00:00"
    mock_db.get_event_users.return_value = [(101, None), (102, None), (103, None), (104, None)]
    mock_db.compose_full_name.side_effect = lambda uid: f"Player_{uid}"
    mock_db.get_payment_status.return_value = False
    mock_db.get_event_extra1.return_value = None

    mocker.patch("os.getenv", return_value=None)

    def translate(t):
        return t

    result = create_event_full_text(chat_id, translate)

    assert "RESERVE" in result
    # Check that Player_101 and Player_102 are before RESERVE, and Player_103 is after
    parts = result.split("RESERVE")
    assert "Player_101" in parts[0]
    assert "Player_102" in parts[0]
    assert "Player_103" in parts[1]
    assert "Player_104" in parts[1]


def test_create_event_full_text_legioneer_attribution(mock_db, mocker):
    chat_id = 123
    mock_db.get_event_text.return_value = "Test Event"
    mock_db.get_event_limit.return_value = 10
    mock_db.get_event_datetime.return_value = "2026-05-01 10:00:00"

    # 10 is a legioneer, 1010 is a regular user. Legioneer was invited by 1010.
    mock_db.get_event_users.return_value = [(10, 1010), (1010, None)]

    def compose_mock(uid):
        if uid == 10:
            return "Legioneer 1"
        if uid == 1010:
            return "John Wick"
        return str(uid)

    mock_db.compose_full_name.side_effect = compose_mock
    mock_db.get_payment_status.return_value = False

    mocker.patch("os.getenv", return_value=None)

    def translate(t):
        return t

    result = create_event_full_text(chat_id, translate)

    # Check for attribution string
    assert "Legioneer 1 (from John Wick)" in result
    assert "John Wick" in result
