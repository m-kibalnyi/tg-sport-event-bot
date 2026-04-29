# -*- coding: utf-8 -*-
import os
import sys

# Ensure we can import from the package
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from sport_event_bot.db.base import reconnect, _exec
except ImportError as e:
    print(f"Could not import database module: {e}")
    print(f"sys.path: {sys.path}")
    sys.exit(1)


def reset_database():
    print("Resetting database...")
    tables = [
        "Participants",
        "Revoked",
        "Thinking",
        "EventLogs",
        "Penalties",
        "Events",
        "Chats",
        "Users"
    ]
    
    conn = reconnect()
    try:
        # We use CASCADE to handle foreign key constraints
        table_list = ", ".join(tables)
        print(f"Truncating tables: {table_list}")
        _exec(conn, f"TRUNCATE TABLE {table_list} CASCADE;")
        print("Database reset successfully.")
    except Exception as e:
        print(f"Error resetting database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    confirm = input("This will delete ALL data in the database. Are you sure? (y/N): ")
    if confirm.lower() == 'y':
        reset_database()
    else:
        print("Aborted.")
