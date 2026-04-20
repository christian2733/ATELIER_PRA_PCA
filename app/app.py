import os
import sqlite3
import time
from datetime import datetime
from flask import Flask, jsonify, request

DB_PATH    = os.getenv("DB_PATH",    "/data/app.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backup")

app = Flask(__name__)

# ---------- DB helpers ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# ---------- Routes ----------

@app.get("/")
def hello():
    init_db()
    return jsonify(status="Bonjour tout le monde !")


@app.get("/health")
def health():
    init_db()
    return jsonify(status="ok")

@app.get("/add")
def add():
    init_db()

    msg = request.args.get("message", "hello")
    ts = datetime.utcnow().isoformat() + "Z"

    conn = get_conn()
    conn.execute(
        "INSERT INTO events (ts, message) VALUES (?, ?)",
        (ts, msg)
    )
    conn.commit()
    conn.close()

    return jsonify(
        status="added",
        timestamp=ts,
        message=msg
    )

@app.get("/consultation")
def consultation():
    init_db()

    conn = get_conn()
    cur = conn.execute(
        "SELECT id, ts, message FROM events ORDER BY id DESC LIMIT 50"
    )

    rows = [
        {"id": r[0], "timestamp": r[1], "message": r[2]}
        for r in cur.fetchall()
    ]

    conn.close()

    return jsonify(rows)

@app.get("/count")
def count():
    init_db()

    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM events")
    n = cur.fetchone()[0]
    conn.close()

    return jsonify(count=n)

@app.get("/status")
def status():
    init_db()

    # --- 1. Nombre d'événements en base ---
    conn = get_conn()
    cur = conn.execute("SELECT COUNT(*) FROM events")
    event_count = cur.fetchone()[0]
    conn.close()

    # --- 2. Dernier fichier de backup ---
    last_backup_file = None
    backup_age_seconds = None

    if os.path.isdir(BACKUP_DIR):
        backup_files = [
            f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")
        ]
        if backup_files:
            # Trier par date de modification, prendre le plus récent
            backup_files.sort(
                key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f)),
                reverse=True
            )
            last_backup_file = backup_files[0]
            mtime = os.path.getmtime(os.path.join(BACKUP_DIR, last_backup_file))
            backup_age_seconds = int(time.time() - mtime)

    return jsonify(
        count=event_count,
        last_backup_file=last_backup_file,
        backup_age_seconds=backup_age_seconds
    )

# ---------- Main ----------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)
