"""Utility script for migrating an existing sqlite database to the
current schema used by the bot.

Run it before starting the new version or as part of deployment:

    python migrate_db.py path/to/tests.db

If no path is supplied, it defaults to "tests.db" in the current
working directory.

The script is intentionally small; it only adds missing columns or
other trivial alterations so that the new code can run without
`sqlite3.OperationalError` exceptions.  A simple migrations table is
used to prevent the same ALTER statement from running multiple times.
You can extend the MIGRATIONS list with future operations as needed.
"""

import sqlite3
import sys
from datetime import datetime

# each entry is a tuple (name, sql) - the name is recorded in
# _migrations so we don't reapply it.
MIGRATIONS = [
    (
        "add_photo_path_column",
        "ALTER TABLE tests ADD COLUMN photo_path TEXT",
    ),
]


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ensure we have a simple bookkeeping table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS _migrations (
            name TEXT PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    conn.commit()

    for name, sql in MIGRATIONS:
        cursor.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,))
        if cursor.fetchone():
            print(f"{name}: already applied")
            continue

        try:
            print(f"applying migration {name}...")
            cursor.execute(sql)
            cursor.execute("INSERT INTO _migrations(name) VALUES(?)", (name,))
            conn.commit()
            print(f"{name}: done")
        except sqlite3.OperationalError as e:
            # column might already exist or other issue; skip but warn
            print(f"{name}: skipped ({e})")
            conn.rollback()

    conn.close()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "tests.db"
    print(f"migrating {path}")
    migrate(path)
