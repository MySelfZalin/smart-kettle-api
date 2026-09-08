import hashlib
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path("data/users.sqlite3")


def init_db(
    default_username: Optional[str] = None,
    default_password: Optional[str] = None,
    default_user_id: str = "admin",
) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt BYTES NOT NULL
            )
            """
        )
        conn.commit()

        if default_username and default_password:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                salt = os.urandom(16)
                pwd_hash = _hash_password(default_password, salt)
                conn.execute(
                    "INSERT OR IGNORE INTO users (user_id, username, password_hash, salt) VALUES (?, ?, ?, ?)",
                    (default_user_id, default_username, pwd_hash, salt),
                )
                conn.commit()


def _hash_password(password: str, salt: bytes) -> str:
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return key.hex()


def create_user(user_id: str, username: str, password: str) -> None:
    salt = os.urandom(16)
    pwd_hash = _hash_password(password, salt)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, password_hash, salt) VALUES (?, ?, ?, ?)",
            (user_id, username, pwd_hash, salt),
        )
        conn.commit()


def authenticate_user(username: str, password: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, password_hash, salt FROM users WHERE username = ?", (username,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        user_id, pwd_hash, salt = row
        expected_hash = _hash_password(password, salt)

        if secrets.compare_digest(pwd_hash, expected_hash):
            return user_id

    return None
