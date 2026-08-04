"""SQLite data access for Spendly.

The only intended data-access layer for the app — routes talk to SQLite through
these helpers, never through their own connections.
"""

import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

# Anchored to the repo root via __file__ so the path holds regardless of CWD.
DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

# The fixed category vocabulary. Forms and summaries should import this rather
# than repeating the strings.
CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def get_db():
    """Return a new connection with dict-like rows and foreign keys enforced.

    The caller owns the connection and is responsible for closing it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Not persistent — SQLite defaults this off on every new connection.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the tables if they don't exist. Safe to call on every startup."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert demo data for development, once.

    Returns True if data was inserted, False if the database was already seeded.
    """
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            return False

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        today = date.today()

        def day(n):
            """Format a day of the current month, never past today."""
            return f"{today.year:04d}-{today.month:02d}-{min(n, today.day):02d}"

        # One row per category, plus a second Food entry to make eight.
        expenses = [
            (user_id, 1500.00, "Bills", day(1), "Electricity bill"),
            (user_id, 320.50, "Food", day(1), "Groceries"),
            (user_id, 80.00, "Transport", day(2), "Metro card top-up"),
            (user_id, 450.00, "Health", day(2), "Pharmacy"),
            (user_id, 299.00, "Entertainment", day(3), "Streaming subscription"),
            (user_id, 1250.00, "Shopping", day(3), "Running shoes"),
            (user_id, 210.00, "Other", day(4), None),
            (user_id, 185.75, "Food", day(4), "Lunch with a friend"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        conn.commit()
        return True
    finally:
        conn.close()
