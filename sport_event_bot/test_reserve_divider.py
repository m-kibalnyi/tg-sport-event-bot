import sys
import os
from unittest.mock import MagicMock

# Mock the database and telegraph modules before importing bot
sys.modules['db_postgres'] = MagicMock()
sys.modules['telegraph'] = MagicMock()

import bot

def test_reserve_divider():
    translate = lambda t: f"TR({t})"
    
    # Setup mock data
    bot.db.get_event_text.return_value = "Football Game"
    bot.db.get_event_limit.return_value = 2
    bot.db.get_event_datetime.return_value = "2026-04-20 18:00:00"
    bot.db.get_event_users.return_value = [(101, None), (102, None), (103, None), (104, None)] # 4 players, limit is 2
    bot.db.compose_full_name.side_effect = lambda uid: f"Player_{uid}"
    bot.db.get_chat_user_rp.return_value = (10, 0)
    bot.db.get_event_revoked_users.return_value = []
    bot.db.get_thinking_users.return_value = []
    bot.db.get_active_penalties.return_value = []
    bot.db.get_event_payment_url.return_value = None
    bot.db.get_event_telegraph_url.return_value = None
    bot.db.get_payment_status.return_value = False
    bot.db.get_event_blik_phone.return_value = None
    bot.db.get_event_extra1.return_value = None
    
    print("--- Testing Reserve Divider ---")
    result = bot.create_event_full_text(12345, translate)
    print(result)
    
    assert "TR(RESERVE)" in result
    assert "1. ✅ Player_101" in result
    assert "2. ✅ Player_102" in result
    assert "3. ✅ Player_103" in result
    assert "4. ✅ Player_104" in result
    
    # Check if divider is between 2 and 3
    parts = result.split("=====================")
    assert "2. " in parts[0]
    assert "3. " in parts[1]
    
    print("\nTest Passed!")

if __name__ == "__main__":
    test_reserve_divider()
