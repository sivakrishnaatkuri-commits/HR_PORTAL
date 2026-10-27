
import sqlite3
from pathlib import Path

db_path = Path("data/talentsphere.db")

if not db_path.exists():
    print("Database not found:", db_path.resolve())
else:
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    print("Database:", db_path.resolve())
    print("Tables:", [row[0] for row in tables])
