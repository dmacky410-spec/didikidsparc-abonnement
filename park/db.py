"""Base de données SQLite — schéma et initialisation."""
import os
import sqlite3
import secrets
from datetime import datetime

DATA_DIR = os.environ.get("DIDIKIDS_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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
  role          TEXT NOT NULL CHECK (role IN ('superadmin','admin','agent')),
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
  member_id       INTEGER REFERENCES members(id),   -- NULL = visiteur (vente rapide)
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
  user_id         INTEGER REFERENCES users(id),
  free_reward     INTEGER NOT NULL DEFAULT 0   -- 1 = visite offerte (fidélité)
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

DEFAULT_PASSWORD = "admin123"

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
    "loyalty_enabled": "1",
    "loyalty_threshold": "10",       # visites payantes avant une visite offerte
    "whatsapp_expiry_template": (
        "Bonjour {parent} ! 🐻 L'abonnement de {enfant} au Didikids Parc "
        "expire le {expiration} ({restantes} entrée(s) restante(s)). "
        "Souhaitez-vous le renouveler ? À très bientôt !"),
    "whatsapp_birthday_template": (
        "Bonjour {parent} ! 🎂 L'anniversaire de {enfant} approche ({date}). "
        "Le Didikids Parc organise des fêtes inoubliables : mini-foot, piscine à balles, "
        "toboggan, zone Lego et arcade. Voulez-vous réserver ?"),
}


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect():
    """Nouvelle connexion (une par requête — sûr en multi-thread)."""
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_roles(conn):
    """Anciennes bases : ajoute le rôle 'superadmin' (contrainte CHECK à reconstruire)."""
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if not row or "superadmin" in row[0]:
        return
    conn.executescript("""
        PRAGMA foreign_keys=OFF;
        CREATE TABLE users_new (
          id            INTEGER PRIMARY KEY AUTOINCREMENT,
          username      TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          role          TEXT NOT NULL CHECK (role IN ('superadmin','admin','agent')),
          employee_id   INTEGER REFERENCES employees(id),
          active        INTEGER NOT NULL DEFAULT 1,
          created_at    TEXT NOT NULL
        );
        INSERT INTO users_new SELECT * FROM users;
        DROP TABLE users;
        ALTER TABLE users_new RENAME TO users;
        PRAGMA foreign_keys=ON;
    """)
    # Le premier administrateur devient super administrateur
    first_admin = conn.execute(
        "SELECT id FROM users WHERE role='admin' AND active=1 ORDER BY id LIMIT 1").fetchone()
    if first_admin and not conn.execute(
            "SELECT 1 FROM users WHERE role='superadmin'").fetchone():
        conn.execute("UPDATE users SET role='superadmin' WHERE id=?", (first_admin[0],))


def _migrate_columns(conn):
    """Ajoute les colonnes apparues après la première version."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(visits)")}
    if "free_reward" not in cols:
        conn.execute("ALTER TABLE visits ADD COLUMN free_reward INTEGER NOT NULL DEFAULT 0")

    # payments.member_id devient nullable (ventes rapides sans fiche membre)
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='payments'").fetchone()
    if row and "member_id       INTEGER NOT NULL REFERENCES members(id)" in row[0]:
        conn.executescript("""
            PRAGMA foreign_keys=OFF;
            CREATE TABLE payments_new (
              id              INTEGER PRIMARY KEY AUTOINCREMENT,
              receipt_number  TEXT NOT NULL UNIQUE,
              subscription_id INTEGER REFERENCES subscriptions(id),
              member_id       INTEGER REFERENCES members(id),
              amount          INTEGER NOT NULL,
              method          TEXT NOT NULL DEFAULT 'especes',
              note            TEXT,
              paid_at         TEXT NOT NULL,
              user_id         INTEGER REFERENCES users(id)
            );
            INSERT INTO payments_new SELECT id, receipt_number, subscription_id, member_id,
                   amount, method, note, paid_at, user_id FROM payments;
            DROP TABLE payments;
            ALTER TABLE payments_new RENAME TO payments;
            CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(paid_at);
            PRAGMA foreign_keys=ON;
        """)


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    _migrate_roles(conn)
    _migrate_columns(conn)

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

    # Compte super administrateur initial.
    # En cloud, définir ADMIN_USERNAME / ADMIN_PASSWORD évite le mot de passe par défaut.
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        from park.auth import hash_password
        username = os.environ.get("ADMIN_USERNAME", "admin").strip() or "admin"
        password = os.environ.get("ADMIN_PASSWORD", "").strip() or DEFAULT_PASSWORD
        conn.execute(
            "INSERT INTO employees (full_name, position, hired_at) VALUES (?,?,?)",
            ("Administrateur", "Super administrateur", now_iso()[:10]),
        )
        emp_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO users (username, password_hash, role, employee_id, created_at) VALUES (?,?,?,?,?)",
            (username, hash_password(password), "superadmin", emp_id, now_iso()),
        )

    conn.commit()
    conn.close()


def get_setting(conn, key, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default
