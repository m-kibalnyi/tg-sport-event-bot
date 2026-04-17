import sys
import os
from unittest.mock import MagicMock

# Mock the database and telegraph modules
sys.modules['sport_event_bot.db_postgres'] = MagicMock()
sys.modules['sport_event_bot.telegraph'] = MagicMock()
sys.modules['sport_event_bot.db.base'] = MagicMock()

import sport_event_bot.ui.render as render
import sport_event_bot.db_postgres as db

def test_legioneer_attribution():
    def translate(t): return t
    
    # Mock data
    db.get_event_text.return_value = "Test Event"
    db.get_event_limit.return_value = 10
    db.get_event_datetime.return_value = "2026-05-01 10:00:00"
    db.get_event_location.return_value = None
    db.get_event_payment_url.return_value = None
    db.get_event_telegraph_url.return_value = None
    db.get_event_blik_phone.return_value = None
    db.get_event_extra1.return_value = None
    db.get_payment_status.return_value = False
    
    # 10 is a legioneer, 1010 is a regular user
    db.get_event_users.return_value = [(10, 1010), (1010, None)]
    db.get_event_id_by_chat_id.return_value = 100
    
    def compose_mock(uid):
        if uid == 10: return "Legioneer 1"
        if uid == 1010: return "John Wick"
        return str(uid)
    db.compose_full_name.side_effect = compose_mock
    
    os.environ['PAYMENTS_PAGE_URL'] = 'https://example.com/event.php'
    
    print("--- Testing Legioneer Attribution ---")
    text = render.create_event_full_text(12345, translate)
    print(text)
    
    assert "1. ➕ Legioneer 1 (from John Wick)" in text
    assert "2. ✅ John Wick" in text
    assert "🔗 <a href='https://example.com/event.php?event=100'>Payments П</a>" in text
    
    print("Test Passed!")

if __name__ == "__main__":
    test_legioneer_attribution()
