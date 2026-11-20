"""Async SQLite database layer using aiosqlite."""

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(__file__).resolve().parent / "parental_control.db"

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the shared database connection."""
    if _db is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _db


async def init_db() -> None:
    """Open the connection and create tables if they don't exist."""
    global _db
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(str(DB_PATH))
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id     TEXT PRIMARY KEY,
            device_name   TEXT NOT NULL,
            device_model  TEXT NOT NULL,
            android_version TEXT NOT NULL,
            app_version   TEXT NOT NULL,
            is_online     INTEGER NOT NULL DEFAULT 1,
            last_seen     TEXT NOT NULL,
            registered_at TEXT NOT NULL
        )
    """)

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id            TEXT PRIMARY KEY,
            device_id     TEXT NOT NULL,
            command_type  TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'pending',
            screenshot_id TEXT,
            created_at    TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        )
    """)

    await _db.execute("""
        CREATE TABLE IF NOT EXISTS screenshots (
            screenshot_id TEXT PRIMARY KEY,
            device_id     TEXT NOT NULL,
            command_id    TEXT NOT NULL,
            filename      TEXT NOT NULL,
            file_size     INTEGER NOT NULL,
            created_at    TEXT NOT NULL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id),
            FOREIGN KEY (command_id) REFERENCES commands(id)
        )
    """)

    await _db.commit()
    logger.info("Database initialised at %s", DB_PATH)


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")
