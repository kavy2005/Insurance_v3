"""
database.py  —  InsureIQ v3 SQLite Auth & History Engine
"""

import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "insurance_app.db"


def _hash_password(password: str) -> str:
    salt = "insureiq_v3_salt_2024"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                email         TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER NOT NULL,
                age                INTEGER,
                weight             REAL,
                height             REAL,
                bmi                REAL,
                income_lpa         REAL,
                smoker             INTEGER,
                city               TEXT,
                occupation         TEXT,
                predicted_category TEXT,
                created_at         TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


# ── User CRUD ─────────────────────────────────────────────────────────────────

def create_user(username: str, email: str, password: str) -> dict:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (username.strip(), email.strip().lower(),
                 _hash_password(password), datetime.utcnow().isoformat())
            )
        return {"success": True}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return {"success": False, "error": "Username already taken."}
        elif "email" in str(e):
            return {"success": False, "error": "Email already registered."}
        return {"success": False, "error": str(e)}


def authenticate_user(username: str, password: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ?",
            (username.strip(), _hash_password(password))
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def update_password(user_id: int, new_password: str) -> bool:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user_id)
        )
    return True


def delete_user(user_id: int) -> bool:
    with get_connection() as conn:
        conn.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return True


# ── Predictions ───────────────────────────────────────────────────────────────

def save_prediction(user_id: int, input_data: dict, predicted_category: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO predictions
               (user_id, age, weight, height, bmi, income_lpa, smoker, city,
                occupation, predicted_category, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                input_data.get("age"),
                input_data.get("weight"),
                input_data.get("height"),
                input_data.get("bmi"),
                input_data.get("income_lpa"),
                int(input_data.get("smoker", False)),
                input_data.get("city"),
                input_data.get("occupation"),
                predicted_category,
                datetime.utcnow().isoformat(),
            )
        )


def get_user_predictions(user_id: int, limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_predictions_flat() -> list[dict]:
    """Returns all predictions (anonymous) for social benchmarking — Feature 5."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT age, city, occupation, predicted_category, created_at FROM predictions ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


# ── Admin ─────────────────────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, email, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_predictions_admin() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.*, u.username FROM predictions p
               JOIN users u ON p.user_id = u.id
               ORDER BY p.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_prediction_stats(user_id: int) -> dict:
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        dist = conn.execute(
            "SELECT predicted_category, COUNT(*) as cnt FROM predictions WHERE user_id = ? GROUP BY predicted_category",
            (user_id,)
        ).fetchall()
        latest = conn.execute(
            "SELECT predicted_category, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
    return {
        "total":          total,
        "distribution":   {row["predicted_category"]: row["cnt"] for row in dist},
        "latest_category": dict(latest)["predicted_category"] if latest else None,
        "latest_date":     dict(latest)["created_at"][:10] if latest else None,
    }


init_db()
