"""Base de données SQLite — schéma et initialisation."""
import os
import sqlite3
import secrets
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "didikidsparc.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS employees (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name  TEXT NOT NULL,
  phone      TEXT,
  position   TEXT,
  hired_at   TEXT,
  active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin','agent')),
  employee_id   INTEGER REFERENCES employees(id),
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token      TEXT PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  code        TEXT NOT NULL UNIQUE,
  child_name  TEXT NOT NULL,
  parent_name TEXT,
  phone       TEXT,
  email       TEXT,
  birth_date  TEXT,
  notes       TEXT,
  active      INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rfid_cards (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  uid          TEXT NOT NULL UNIQUE,
  card_number  TEXT,
  member_id    INTEGER NOT NULL REFERENCES members(id),
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','blocked')),
  assigned_at  TEXT NOT NULL,
  blocked_at   TEXT,
  block_reason TEXT
);

CREATE TABLE IF NOT EXISTS subscription_types (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  price         INTEGER NOT NULL,
  entries       INTEGER,              -- NULL = illimité
  validity_days INTEGER NOT NULL,
  active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id     INTEGER NOT NULL REFERENCES members(id),
  type_id       INTEGER NOT NULL REFERENCES subscription_types(id),
  start_date    TEXT NOT NULL,
  end_date      TEXT NOT NULL,
  entries_total INTEGER,
  entries_left  INTEGER,
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled')),
  created_at    TEXT NOT NULL,
  created_by    INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS payments (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  receipt_number  TEXT NOT NULL UNIQUE,
  subscription_id INTEGER REFERENCES subscriptions(id),
  member_id       INTEGER NOT NULL REFERENCES members(id),
  amount          INTEGER NOT NULL,
  method          TEXT NOT NULL DEFAULT 'especes',
  note            TEXT,
  paid_at         TEXT NOT NULL,
  user_id         INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS visits (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id       INTEGER REFERENCES members(id),
  subscription_id INTEGER REFERENCES subscriptions(id),
  card_uid        TEXT,
  result          TEXT NOT NULL CHECK (result IN ('ok','refused')),
  refusal_reason  TEXT,
  visited_at      TEXT NOT NULL,
  user_id         INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);

CREATE INDEX IF NOT EXISTS idx_cards_member    ON rfid_cards(member_id);
CREATE INDEX IF NOT EXISTS idx_subs_member     ON subscriptions(member_id);
CREATE INDEX IF NOT EXISTS idx_visits_date     ON visits(visited_at);
CREATE INDEX IF NOT EXISTS idx_visits_member   ON visits(member_id);
CREATE INDEX IF NOT EXISTS idx_payments_date   ON payments(paid_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
"""

DEFAULT_TYPES = [
    ("Entrée simple", 50000, 1, 1),
    ("Mensuel 4 entrées", 180000, 4, 30),
    ("Mensuel 8 entrées", 320000, 8, 30),
    ("VIP Illimité", 500000, None, 30),
]

DEFAULT_SETTINGS = {
    "park_name": "Didikids Parc",
    "receipt_footer": "Merci de votre visite ! Parce que chaque enfant mérite de s'épanouir.",
    "park_phone": "",
    "park_address": "Conakry, Guinée",
}


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect():
    """Nouvelle connexion (une par requête — sûr en multi-thread)."""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)

    # Types d'abonnements par défaut
    if conn.execute("SELECT COUNT(*) FROM subscription_types").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO subscription_types (name, price, entries, validity_days) VALUES (?,?,?,?)",
            DEFAULT_TYPES,
        )

    # Paramètres par défaut
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (key, value))

    # Jeton pour le pont RFID (lecteur ACR122U)
    if conn.execute("SELECT 1 FROM settings WHERE key='scan_token'").fetchone() is None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('scan_token', ?)",
            (secrets.token_hex(16),),
        )

    # Compte administrateur par défaut (mot de passe à changer à la première connexion)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        from park.auth import hash_password
        conn.execute(
            "INSERT INTO employees (full_name, position, hired_at) VALUES (?,?,?)",
            ("Administrateur", "Gérant", now_iso()[:10]),
        )
        emp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO users (username, password_hash, role, employee_id, created_at) VALUES (?,?,?,?,?)",
            ("admin", hash_password("admin123"), "admin", emp_id, now_iso()),
        )

    conn.commit()
    conn.close()


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default
