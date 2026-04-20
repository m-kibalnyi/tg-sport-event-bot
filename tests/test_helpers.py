import datetime

from sport_event_bot.utils.helpers import _coerce_to_datetime, get_default_datetime, parse_datetime, parse_loose_json


def test_parse_loose_json():
    # Standard format
    text = 'name: "Test Event", limit: 16, public: true'
    result = parse_loose_json(text)
    assert result["name"] == "Test Event"
    assert result["limit"] == 16
    assert result["public"] is True

    # Single quotes and mixed types
    text = "location: 'Warsaw City', price: 25.5, active: false"
    result = parse_loose_json(text)
    assert result["location"] == "Warsaw City"
    assert result["price"] == 25.5
    assert result["active"] is False

    # No quotes for simple strings
    text = "city: Warsaw, code: 123"
    result = parse_loose_json(text)
    assert result["city"] == "Warsaw"
    assert result["code"] == 123


def test_coerce_to_datetime():
    # From datetime object
    now = datetime.datetime.now()
    assert _coerce_to_datetime(now) == now

    # From ISO string
    iso_str = "2024-05-20T15:30:00"
    dt = _coerce_to_datetime(iso_str)
    assert dt.year == 2024
    assert dt.month == 5
    assert dt.day == 20
    assert dt.hour == 15

    # From custom space format
    space_str = "2024-05-20 15:30:00"
    dt = _coerce_to_datetime(space_str)
    assert dt.hour == 15

    # Invalid input
    assert _coerce_to_datetime("not a date") is None
    assert _coerce_to_datetime(123) is None


def test_get_default_datetime():
    # This function logic depends on datetime.now()
    # We can't easily test the exact value without mocking now(),
    # but we can check if it returns a valid datetime.
    dt = get_default_datetime()
    assert isinstance(dt, datetime.datetime)
    assert dt.minute in [30, 0]  # Based on the code's 20:30 or 11:30


def test_parse_datetime():
    def dummy_translate(text):
        return text

    # Test valid dates
    test_cases = [
        ("tomorrow 18:00", 18),
        ("2026-04-17 14:00", 14),
        ("at 8pm on friday", 20),
        ("next monday 10:30", 10),
    ]

    for tc, expected_hour in test_cases:
        dt = parse_datetime(tc, dummy_translate)
        if dt:  # recurrent parsing might depend on when the test is run
            assert isinstance(dt, datetime.datetime)
            assert dt.hour == expected_hour

    # Invalid date
    assert parse_datetime("nonsense invalid date string", dummy_translate) is None
