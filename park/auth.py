"""Authentification — hachage scrypt et sessions."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from park import db

SESSION_HOURS = 14  # une journée de travail


PBKDF2_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                     bytes.fromhex(salt_hex), PBKDF2_ITERATIONS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def create_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
        (token, user_id,
         now.strftime("%Y-%m-%d %H:%M:%S"),
         (now + timedelta(hours=SESSION_HOURS)).strftime("%Y-%m-%d %H:%M:%S")),
    )
    # Nettoyage des sessions expirées
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (db.now_iso(),))
    return token


def get_user_by_token(conn, token: str):
    if not token:
        return None
    return conn.execute(
        """SELECT u.id, u.username, u.role, u.employee_id, e.full_name
           FROM sessions s
           JOIN users u ON u.id = s.user_id
           LEFT JOIN employees e ON e.id = u.employee_id
           WHERE s.token = ? AND s.expires_at >= ? AND u.active = 1""",
        (token, db.now_iso()),
    ).fetchone()


def delete_session(conn, token: str):
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
