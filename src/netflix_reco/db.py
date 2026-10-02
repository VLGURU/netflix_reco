import sqlite3
from datetime import datetime
from .config import DB_PATH, DATA_DIR


def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            user_id TEXT NOT NULL,
            rating INTEGER,
            text TEXT,
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            query TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            show_id TEXT NOT NULL,
            title TEXT NOT NULL,
            item_type TEXT NOT NULL,
            genres TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def log_query(user_id: str, query: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO query_log(user_id, query, created_at) VALUES (?, ?, ?)",
            (user_id, query, datetime.utcnow().isoformat())
        )


def add_review(user_id: str, title: str, rating: int | None, text: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reviews(title, user_id, rating, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (title, user_id, rating, text, datetime.utcnow().isoformat())
        )


def add_like(user_id: str, show_id: str, title: str, item_type: str, genres_csv: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO likes(user_id, show_id, title, item_type, genres, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, show_id, title, item_type, genres_csv, datetime.utcnow().isoformat())
        )