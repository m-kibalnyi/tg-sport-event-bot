import os
import sys

# Mocking db and translate
class MockDB:
    def get_event_text(self, chat_id): return "Test"
    def get_event_limit(self, chat_id): return 18
    def get_event_datetime(self, chat_id): return "2026-04-19 11:35"
    def get_event_location(self, chat_id): return None
    def get_event_payment_url(self, chat_id): return None
    def get_event_telegraph_url(self, chat_id): return None
    def get_event_blik_phone(self, chat_id): return None
    def get_event_id_by_chat_id(self, chat_id): return 26
    def get_event_extra1(self, chat_id): return None
    def get_event_users(self, chat_id): return []
    def get_thinking_users(self, chat_id): return []
    def get_event_revoked_users(self, chat_id): return []
    def get_active_penalties(self, chat_id): return []
    def get_payment_status(self, chat_id, uid): return False
    def compose_full_name(self, uid): return "User"

sys.modules['sport_event_bot.db_postgres'] = MockDB()
sys.modules['sport_event_bot.utils.helpers'] = type('Helpers', (), {'parse_datetime': lambda x,y: None})

import sport_event_bot.ui.render as render

os.environ['PAYMENTS_PAGE_URL'] = 'http://localhost:8000/event.php'

def translate(t):
    mapping = {
        'Payment link': 'Payment link',
        'Payments': 'Оплаты',
        'Stats': 'Stats',
        'Logs': 'Logs',
        'Event Logs': 'Event Logs'
    }
    return mapping.get(t, t)

text = render.create_event_full_text(12345, translate)
print("RAW TEXT:")
print(repr(text))
print("---")
print(text)
