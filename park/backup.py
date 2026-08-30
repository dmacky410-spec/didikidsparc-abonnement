"""Sauvegardes automatiques de la base de données.

Une copie datée est créée au démarrage puis toutes les 24 h, sans que
personne ait à y penser. La copie utilise l'API de sauvegarde SQLite :
elle reste fiable même si un employé travaille au même moment.
"""
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime

from park import db

KEEP_DAYS = 30          # nombre de sauvegardes conservées
INTERVAL_SECONDS = 24 * 3600


def backup_dir(conn=None):
    """Dossier de destination : réglable, sinon « sauvegardes » à côté des données."""
    own_conn = conn is None
    if own_conn:
        conn = db.connect()
    try:
        configured = db.get_setting(conn, "backup_dir", "") or ""
    finally:
        if own_conn:
            conn.close()
    return configured.strip() or os.path.join(db.DATA_DIR, "sauvegardes")


def backup_now(dest_dir=None):
    """Crée une copie datée. Retourne (chemin, taille en octets)."""
    dest_dir = dest_dir or backup_dir()
    os.makedirs(dest_dir, exist_ok=True)
    name = "didikidsparc_%s.db" % datetime.now().strftime("%Y-%m-%d_%Hh%M")
    path = os.path.join(dest_dir, name)

    source = sqlite3.connect(db.DB_PATH)
    target = sqlite3.connect(path)
    try:
        source.backup(target)      # copie cohérente, même base ouverte
        # Fichier unique : sans journal séparé, la restauration se résume
        # à recopier ce seul .db
        target.execute("PRAGMA journal_mode=DELETE")
        target.commit()
    finally:
        target.close()
        source.close()
    for extra in (path + "-wal", path + "-shm"):
        try:
            os.remove(extra)
        except OSError:
            pass
    cleanup_old(dest_dir)
    return path, os.path.getsize(path)


def cleanup_old(dest_dir, keep=KEEP_DAYS):
    """Ne garde que les `keep` sauvegardes les plus récentes."""
    try:
        files = sorted(
            (f for f in os.listdir(dest_dir)
             if f.startswith("didikidsparc_") and f.endswith(".db")),
            reverse=True)
        for old in files[keep:]:
            os.remove(os.path.join(dest_dir, old))
    except OSError:
        pass


def list_backups(dest_dir=None):
    dest_dir = dest_dir or backup_dir()
    result = []
    try:
        for name in sorted(os.listdir(dest_dir), reverse=True):
            if not (name.startswith("didikidsparc_") and name.endswith(".db")):
                continue
            full = os.path.join(dest_dir, name)
            stat = os.stat(full)
            result.append({
                "name": name,
                "size_kb": round(stat.st_size / 1024),
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    except OSError:
        pass
    return {"folder": dest_dir, "backups": result}


def free_space_mb(path):
    try:
        return round(shutil.disk_usage(path).free / (1024 * 1024))
    except OSError:
        return None


def start_scheduler():
    """Lance la sauvegarde périodique en tâche de fond."""
    def loop():
        while True:
            try:
                path, size = backup_now()
                print(f"[sauvegarde] {path} ({size // 1024} Ko)")
            except Exception as e:
                print(f"[sauvegarde] echec : {e}")
            time.sleep(INTERVAL_SECONDS)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
