
"""
SQLite database setup for Assignment A.

Sensitive customer information is encrypted or represented by
a keyed phone hash before it is stored.
"""

import sqlite3
from pathlib import Path


# Database file will be created in the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "assignment.db"


def get_connection():
    """Create and return a SQLite database connection."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    """Create all required database tables if they do not exist."""

    connection = get_connection()

    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                phone_hash TEXT NOT NULL,
                phone_encrypted TEXT NOT NULL,
                customer_name_encrypted TEXT NOT NULL,
                reference_value TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                fields_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(workflow_id, phone_hash)
            );


            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                call_id TEXT,
                occurred_at TEXT,
                phone_hash TEXT,
                payload_json TEXT NOT NULL,
                raw_event_encrypted TEXT NOT NULL,
                received_drop TEXT NOT NULL,
                received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );


            CREATE TABLE IF NOT EXISTS ingested_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );


            CREATE TABLE IF NOT EXISTS rejections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                row_number INTEGER NOT NULL,
                reason TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS event_quarantine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                reason TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES events(event_id)
            );


            CREATE INDEX IF NOT EXISTS idx_leads_workflow_phone
            ON leads(workflow_id, phone_hash);


            CREATE INDEX IF NOT EXISTS idx_events_workflow_phone
            ON events(workflow_id, phone_hash);


            CREATE INDEX IF NOT EXISTS idx_events_call_id
            ON events(call_id);


            CREATE INDEX IF NOT EXISTS idx_events_occurred_at
            ON events(occurred_at);
            """
        )

        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
    print(f"Database location: {DB_PATH}")
