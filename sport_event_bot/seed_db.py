import sys
import os
import datetime
import random

# Add current directory to path so we can import db_postgres
sys.path.append(os.path.join(os.getcwd(), 'sport_event_bot'))

import db_postgres as db

def seed():
    print("Starting database seeding...")
    db.init_database()
    
    chat_id = -100123456789 # Sample chat ID
    db.register_new_chat_id(chat_id, 'ru')
    
    # Create some users
    users = [
        (1001, "Ivan", "Ivanov", "ivan_i"),
        (1002, "Petr", "Petrov", "petr_p"),
        (1003, "Sidor", "Sidorov", "sidor_s"),
        (1004, "Alex", "Alexeev", "alex_a"),
        (1005, "Dmitry", "Dmitriev", "dmitry_d"),
    ]
    
    for uid, fn, ln, un in users:
        db.add_or_update_user(uid, fn, ln, un)
    
    # Create some past events
    now = datetime.datetime.now()
    for i in range(5):
        dt = now - datetime.timedelta(days=(i+1)*7)
        db.event(chat_id, f"Past Match {5-i}", dt, 15, 0, "Past event", users[0][0])
        event_id = db.get_event_id_by_chat_id(chat_id)
        
        # Add random participants to past events
        participants = random.sample(users, random.randint(3, 5))
        for p in participants:
            db.apply_for_participation_in_the_event(chat_id, p[0])
            db.set_payment_status(chat_id, p[0], True)
        
        # Close the event (mark as Fixed)
        db.fix_event(chat_id)

    # Create one open event
    db.event(chat_id, "Upcoming Match 1", now + datetime.timedelta(days=3), 15, 999, "Upcoming match description", users[0][0])
    
    # Add participants to open event
    db.apply_for_participation_in_the_event(chat_id, users[1][0])
    db.apply_for_participation_in_the_event(chat_id, users[2][0])
    db.apply_for_thinking(chat_id, users[3][0])
    db.revoke_application_for_the_event(chat_id, users[4][0])
    
    # Add some yellow cards
    # 1. Active yellow card (default 14 days)
    db.penalty_for_user_in_chat(chat_id, users[1][0], users[0][0])
    
    # 2. Short-term active card (2 days)
    db.penalty_for_user_in_chat(chat_id, users[2][0], users[0][0], ttl_days=2)
    
    # 3. Expired card (from 20 days ago, with 5 days TTL)
    # We need to manually update the timestamp for the expired one since the function uses NOW()
    conn = db.reconnect()
    past_op = now - datetime.timedelta(days=20)
    past_expiry = now - datetime.timedelta(days=15)
    db._exec(conn, 'INSERT INTO Penalties(chat_id, platform, user_id, operation_datetime, operator_id, expires_at) VALUES (%s, %s, %s, %s, %s, %s);',
          (chat_id, db.PLATFORM, users[3][0], past_op, users[0][0], past_expiry))
    conn.close()

    print("Seeding completed successfully!")

if __name__ == "__main__":
    seed()
