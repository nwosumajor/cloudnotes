import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from flask import Flask, g, jsonify, request

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME, port=DB_PORT,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME, port=DB_PORT)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    conn.close()

@app.get("/healthz")
def healthz():
    get_db().cursor().execute("SELECT 1")
    return jsonify({"status": "ok"})

@app.get("/notes")
def list_notes():
    with get_db().cursor() as cur:
        cur.execute("SELECT id, title, body, created_at FROM notes ORDER BY id")
        rows = cur.fetchall()
    return jsonify({"count": len(rows), "notes": [dict(row) for row in rows]})

@app.post("/notes")
def create_note():
    payload = request.get_json(silent=True)
    title, body = str(payload.get("title", "")).strip(), str(payload.get("body", "")).strip()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO notes (title, body, created_at) VALUES (%s, %s, %s) RETURNING id", (title, body, created_at))
        note_id = cur.fetchone()["id"]
        conn.commit()
    return jsonify({"id": note_id, "title": title, "body": body, "created_at": created_at}), 201

@app.delete("/notes/<int:note_id>")
def delete_note(note_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))
        deleted_count = cur.rowcount
        conn.commit()

    if deleted_count == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": note_id})

init_db()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)))
