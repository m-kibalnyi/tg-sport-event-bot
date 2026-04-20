# -*- coding: utf-8 -*-
import os
import sys

import psycopg2
from dotenv import load_dotenv
from loguru import logger
from psycopg2 import extras

# Load environment variables
load_dotenv(".env.development")
load_dotenv()

PLATFORM = "telegram"
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "neondb")
DB_USER = os.getenv("DB_USER", "neondb_owner")
DB_PASS = os.getenv("DB_PASS", "")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSLMODE = os.getenv("DB_SSLMODE", "require")

logger.remove()
logger.add("logs.log", level="DEBUG")
logger.add(sys.stderr, level="DEBUG")


def reconnect():
    """Open a new PostgreSQL connection"""
    conn = psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT, sslmode=DB_SSLMODE
    )
    conn.autocommit = True
    return conn


def _exec(conn, query, params=None):
    cur = conn.cursor()
    cur.execute(query, params or ())
    return cur


def _exec_many(conn, query, seq_of_params):
    cur = conn.cursor()
    extras.execute_values(cur, query, seq_of_params)
    return cur
