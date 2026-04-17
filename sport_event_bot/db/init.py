# -*- coding: utf-8 -*-
try:
    from sport_event_bot.db.base import reconnect, _exec, _exec_many, PLATFORM
except (ImportError, ValueError):
    from .base import reconnect, _exec, _exec_many, PLATFORM

def create_table_users():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Users (
            user_id BIGINT NOT NULL,
            platform VARCHAR(16) NOT NULL DEFAULT 'telegram',
            first_name VARCHAR(255) DEFAULT '',
            last_name  VARCHAR(255) DEFAULT '',
            username   VARCHAR(255) DEFAULT '',
            birth_date VARCHAR(32)  DEFAULT '',
            phone      VARCHAR(64)  DEFAULT '',
            facebook   VARCHAR(255) DEFAULT '',
            lang       VARCHAR(8) DEFAULT 'ru',
            extra      TEXT,
            PRIMARY KEY (user_id, platform)
        );
    ''')
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'users'::regclass AND attname = 'lang') THEN ALTER TABLE Users ADD COLUMN lang VARCHAR(8) DEFAULT 'ru'; END IF; END $$;")
    
    rows = [(uid, PLATFORM, 'Legioneer') for uid in range(10, 1010)]
    query = "INSERT INTO Users (user_id, platform, first_name) VALUES %s ON CONFLICT (user_id, platform) DO NOTHING"
    _exec_many(conn, query, rows)
    conn.close()

def create_table_chats():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Chats (
            chat_id BIGINT NOT NULL,
            platform VARCHAR(16) NOT NULL DEFAULT 'telegram',
            lang VARCHAR(8),
            priority_members TEXT,
            latest_event_id BIGINT DEFAULT 0,
            latest_bot_message_id VARCHAR(64) DEFAULT '',
            latest_bot_message_text TEXT,
            extra1 TEXT,
            extra2 TEXT,
            extra3 TEXT,
            log_thread_id BIGINT DEFAULT NULL,
            lists_thread_id BIGINT DEFAULT NULL,
            PRIMARY KEY (chat_id, platform)
        );
    ''')
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'chats'::regclass AND attname = 'log_thread_id') THEN ALTER TABLE Chats ADD COLUMN log_thread_id BIGINT DEFAULT NULL; END IF; END $$;")
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'chats'::regclass AND attname = 'lists_thread_id') THEN ALTER TABLE Chats ADD COLUMN lists_thread_id BIGINT DEFAULT NULL; END IF; END $$;")
    conn.close()

def create_table_events():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Events (
            event_id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            platform VARCHAR(16) NOT NULL DEFAULT 'telegram',
            status VARCHAR(32) DEFAULT 'Open',
            description TEXT,
            datetime VARCHAR(64) DEFAULT '',
            players_limit INT DEFAULT 0,
            payment_url TEXT DEFAULT NULL,
            telegraph_url TEXT DEFAULT NULL,
            blik_phone VARCHAR(32) DEFAULT NULL,
            latest_bot_message_id VARCHAR(64) DEFAULT '',
            latest_bot_message_text TEXT,
            extra1 TEXT,
            extra2 TEXT,
            extra3 TEXT,
            CONSTRAINT fk_events_chat
              FOREIGN KEY (chat_id, platform) REFERENCES Chats(chat_id, platform)
              ON DELETE SET NULL ON UPDATE CASCADE
        );
    ''')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_events_chat_platform ON Events (chat_id, platform);')
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='blik_phone') THEN ALTER TABLE Events ADD COLUMN blik_phone VARCHAR(32) DEFAULT NULL; END IF; END $$;")
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='creator_id') THEN ALTER TABLE Events ADD COLUMN creator_id BIGINT DEFAULT NULL; END IF; END $$;")
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='location') THEN ALTER TABLE Events ADD COLUMN location TEXT DEFAULT NULL; END IF; END $$;")
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='latest_bot_message_id') THEN ALTER TABLE Events ADD COLUMN latest_bot_message_id VARCHAR(64) DEFAULT ''; END IF; END $$;")
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='events' AND column_name='latest_bot_message_text') THEN ALTER TABLE Events ADD COLUMN latest_bot_message_text TEXT; END IF; END $$;")
    conn.close()

def create_table_participants():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Participants (
            event_id BIGINT NOT NULL,
            user_id BIGINT,
            operation_datetime TIMESTAMP NOT NULL,
            paid BOOLEAN DEFAULT FALSE,
            paid_at TIMESTAMP DEFAULT NULL,
            invited_by BIGINT DEFAULT NULL,
            UNIQUE (event_id, user_id),
            CONSTRAINT fk_part_event
              FOREIGN KEY (event_id) REFERENCES Events(event_id)
              ON DELETE CASCADE ON UPDATE CASCADE
        );
    ''')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_participants_event ON Participants (event_id);')
    conn.close()

def create_table_thinking():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Thinking (
            event_id BIGINT NOT NULL,
            user_id BIGINT,
            operation_datetime TIMESTAMP NOT NULL,
            UNIQUE (event_id, user_id),
            CONSTRAINT fk_think_event
              FOREIGN KEY (event_id) REFERENCES Events(event_id)
              ON DELETE CASCADE ON UPDATE CASCADE
        );
    ''')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_thinking_event ON Thinking (event_id);')
    conn.close()

def create_table_revoked():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Revoked (
            event_id BIGINT NOT NULL,
            user_id BIGINT,
            operation_datetime TIMESTAMP NOT NULL,
            UNIQUE (event_id, user_id),
            CONSTRAINT fk_rev_event
              FOREIGN KEY (event_id) REFERENCES Events(event_id)
              ON DELETE CASCADE ON UPDATE CASCADE
        );
    ''')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_revoked_event ON Revoked (event_id);')
    conn.close()

def create_table_event_logs():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS EventLogs (
            log_id SERIAL PRIMARY KEY,
            event_id BIGINT NOT NULL,
            message TEXT NOT NULL,
            operation_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_log_event
              FOREIGN KEY (event_id) REFERENCES Events(event_id)
              ON DELETE CASCADE ON UPDATE CASCADE
        );
    ''')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_event_logs_event ON EventLogs (event_id);')
    conn.close()

def create_table_chat_penalties():
    conn = reconnect()
    _exec(conn, '''
        CREATE TABLE IF NOT EXISTS Penalties (
            chat_id BIGINT,
            platform VARCHAR(16) NOT NULL DEFAULT 'telegram',
            user_id BIGINT,
            operation_datetime TIMESTAMP NOT NULL,
            operator_id BIGINT,
            expires_at TIMESTAMP,
            CONSTRAINT fk_pen_chat
              FOREIGN KEY (chat_id, platform) REFERENCES Chats(chat_id, platform)
              ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_pen_user
              FOREIGN KEY (user_id, platform) REFERENCES Users(user_id, platform)
              ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT fk_pen_operator
              FOREIGN KEY (operator_id, platform) REFERENCES Users(user_id, platform)
              ON DELETE CASCADE ON UPDATE CASCADE
        );
    ''')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_pen_chat_platform ON Penalties (chat_id, platform);')
    _exec(conn, 'CREATE INDEX IF NOT EXISTS idx_pen_user_platform ON Penalties (user_id, platform);')
    _exec(conn, "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = 'penalties'::regclass AND attname = 'expires_at') THEN ALTER TABLE Penalties ADD COLUMN expires_at TIMESTAMP; END IF; END $$;")
    conn.close()

def init_database():
    """Initialize all tables"""
    create_table_users()
    create_table_chats()
    create_table_events()
    create_table_participants()
    create_table_revoked()
    create_table_chat_penalties()
    create_table_thinking()
    create_table_event_logs()
