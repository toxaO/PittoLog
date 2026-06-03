from __future__ import annotations

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

CURRENT_DB_VERSION = 1


def connect(path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def prepare_database(path: Path | str) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    existed = db_path.exists()
    connection = connect(db_path)
    current_version = get_user_version(connection)
    if existed and current_version < CURRENT_DB_VERSION:
        backup_database(db_path)
    initialize_database(connection)
    connection.execute(f"PRAGMA user_version = {CURRENT_DB_VERSION}")
    connection.commit()
    return connection


def get_user_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def backup_database(db_path: Path) -> Path:
    backup_dir = db_path.parent.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.stem}_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT,
            name TEXT NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT,
            name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_items_active_barcode
            ON items(barcode)
            WHERE active = 1 AND barcode IS NOT NULL;

        CREATE UNIQUE INDEX IF NOT EXISTS idx_departments_active_barcode
            ON departments(barcode)
            WHERE active = 1 AND barcode IS NOT NULL;

        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES items(id),
            department_id INTEGER NOT NULL REFERENCES departments(id),
            loaned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            returned_at TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_open_loans_item
            ON loans(item_id)
            WHERE returned_at IS NULL;

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            item_id INTEGER REFERENCES items(id),
            department_id INTEGER REFERENCES departments(id),
            barcode TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    normalize_existing_barcodes(connection)
    connection.commit()


def normalize_existing_barcodes(connection: sqlite3.Connection) -> None:
    for table, prefix in (("items", "ITEM:"), ("departments", "DEPT:")):
        rows = connection.execute(
            f"SELECT id, barcode FROM {table} WHERE barcode LIKE ?",
            (f"{prefix}+%",),
        ).fetchall()
        for row in rows:
            normalized = f"{prefix}{row['barcode'][len(prefix) + 1:]}"
            duplicate = connection.execute(
                f"SELECT id FROM {table} WHERE barcode = ? AND id != ?",
                (normalized, row["id"]),
            ).fetchone()
            if duplicate is None:
                connection.execute(
                    f"UPDATE {table} SET barcode = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (normalized, row["id"]),
                )
