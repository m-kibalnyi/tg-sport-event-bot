import sys
import os
import datetime

# Add current directory to path so we can import db_postgres
sys.path.append(os.path.join(os.getcwd(), 'sport_event_bot'))

import db_postgres as db
import bot

def test_rendering():
    chat_id = -100123456789
    def translate(t): return t
    
    print("--- Event Message Rendering Test ---")
    text = bot.create_event_full_text(chat_id, translate)
    print(text)
    print("--- End of Test ---")

if __name__ == "__main__":
    test_rendering()
