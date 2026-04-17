import sys
import os
import datetime

# Correct path for imports
sys.path.append(os.getcwd())

try:
    from sport_event_bot.ui.render import create_event_full_text
except ImportError:
    from ui.render import create_event_full_text
try:
    from sport_event_bot.db_postgres import init_database
except ImportError:
    from db_postgres import init_database

def test_rendering():
    chat_id = -100123456789
    def translate(t): return t
    
    # Initialize DB (run migrations)
    print("Initializing Database...")
    try:
        init_database()
    except Exception as e:
        print(f"DB Init Warning: {e}")
    
    print("--- Event Message Rendering Test ---")

    try:
        text = create_event_full_text(chat_id, translate)
        print(text)
    except Exception as e:
        print(f"Error during rendering: {e}")
    print("--- End of Test ---")

if __name__ == "__main__":
    test_rendering()
