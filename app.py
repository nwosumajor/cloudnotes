"""CloudNotes v1 — a small notes API backed by SQLite.

@app.after_request
def add_cors_headers(response):
    ""Allow the S3/CloudFront frontend to call the API from another domain.""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

Routes:
    GET    /notes       list all notes
    POST   /notes       create a note   {"title": "...", "body": "..."}
    DELETE /notes/<id>  delete a note
    GET    /healthz     liveness check (used by later container/monitoring stages)

Configuration comes from environment variables:
    PORT      port to listen on          (default 5000)
    HOST      interface to bind          (default 0.0.0.0)
    NOTES_DB  path to the SQLite file    (default notes.db)
"""

import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request

app = Flask(__name__)

DB_PATH = os.environ.get("NOTES_DB", "notes.db")


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------

def get_db():
    """Return a per-request SQLite connection, creating it on first use.

    Flask's `g` object lives for exactly one request, so each request gets its
    own connection and we never share one across threads.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        # Rows come back as dict-like objects instead of plain tuples.
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Close the connection when the request finishes, even if it errored."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the notes table if it isn't there yet. Safe to run every start."""
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def row_to_note(row):
    """Turn a sqlite3.Row into a plain dict so jsonify can serialize it."""
    return {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "created_at": row["created_at"],
    }


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.get("/healthz")
def healthz():
    """Cheap liveness probe. Touches the DB so a broken volume shows up here."""
    get_db().execute("SELECT 1")
    return jsonify({"status": "ok"})


@app.get("/notes")
def list_notes():
    rows = get_db().execute(
        "SELECT id, title, body, created_at FROM notes ORDER BY id"
    ).fetchall()
    notes = [row_to_note(row) for row in rows]
    return jsonify({"count": len(notes), "notes": notes})


@app.post("/notes")
def create_note():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "request body must be a JSON object"}), 400

    title = str(payload.get("title", "")).strip()
    if not title:
        return jsonify({"error": "'title' is required"}), 400

    body = str(payload.get("body", "")).strip()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    db = get_db()
    cursor = db.execute(
        "INSERT INTO notes (title, body, created_at) VALUES (?, ?, ?)",
        (title, body, created_at),
    )
    db.commit()

    note = {
        "id": cursor.lastrowid,
        "title": title,
        "body": body,
        "created_at": created_at,
    }
    # 201 Created, with a Location header pointing at the new resource.
    return jsonify(note), 201, {"Location": f"/notes/{note['id']}"}


@app.delete("/notes/<int:note_id>")
def delete_note(note_id):
    db = get_db()
    cursor = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    db.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": f"no note with id {note_id}"}), 404
    return jsonify({"deleted": note_id})


# --------------------------------------------------------------------------
# JSON error handlers — keeps every response JSON, never Flask's HTML pages
# --------------------------------------------------------------------------

@app.errorhandler(404)
def handle_404(error):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def handle_405(error):
    return jsonify({"error": "method not allowed"}), 405


@app.errorhandler(500)
def handle_500(error):
    return jsonify({"error": "internal server error"}), 500


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

# Run at import time so `flask run` and gunicorn get a ready table too,
# not just `python3 app.py`.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)
