# cloudnotes
This is a very important project. To master Kubernetes and containerization.
A notes app I'm building to learn DevOps and AWS, one stage at a time.
a simple notes-taking web app. It starts as a few lines of Python running on your laptop, and by the end it is containerized, deployed on Kubernetes, monitored, secured, and architected for multi-region failover on AWS
# CloudNotes v1

A small notes API in Flask, backed by SQLite. This is the application that later
stages of the project will containerize, deploy, and monitor.

## Run it

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

The server comes up on http://localhost:5000. Press Ctrl+C to stop, and
`deactivate` to leave the virtual environment.

## Configuration

Everything is read from the environment, so nothing needs editing to move
between a laptop and a container.

| Variable   | Default   | Purpose                     |
| ---------- | --------- | --------------------------- |
| `PORT`     | `5000`    | Port to listen on           |
| `HOST`     | `0.0.0.0` | Interface to bind           |
| `NOTES_DB` | `notes.db`| Path to the SQLite file     |

```bash
PORT=8080 NOTES_DB=/data/notes.db python3 app.py
```

`HOST` defaults to `0.0.0.0` rather than `127.0.0.1` so the app is reachable
from outside a container later. On a laptop that means other machines on your
network can reach it too — set `HOST=127.0.0.1` if you'd rather it stayed local.

## API

| Method   | Path          | Notes                             |
| -------- | ------------- | --------------------------------- |
| `GET`    | `/notes`      | List all notes                    |
| `POST`   | `/notes`      | Create one. `title` required      |
| `DELETE` | `/notes/<id>` | Delete one. 404 if it isn't there |
| `GET`    | `/healthz`    | Liveness check                    |

```bash
curl localhost:5000/notes

curl -X POST localhost:5000/notes \
  -H 'Content-Type: application/json' \
  -d '{"title": "Buy milk", "body": "2 litres"}'

curl -X DELETE localhost:5000/notes/1
```

Every response is JSON, including errors — a bad request or a missing route
returns `{"error": "..."}` rather than Flask's HTML page. That matters once
something automated is calling this instead of you.

## Regenerating requirements.txt

After installing anything new inside the active venv:

```bash
pip freeze > requirements.txt
```

## Verifying a stranger could run it

```bash
deactivate
rm -rf venv                     # Windows: rmdir /s venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

If it starts and answers `curl localhost:5000/healthz`, the repo is
self-contained. This exact sequence was run against the files here.

## What isn't in here

Flask's built-in server prints a warning about not being for production, and
it's right — it's single-threaded and has no request timeouts. Swapping in
gunicorn is a deployment-stage concern, not a v1 one.

There's also no auth and no per-user separation: anyone who can reach the port
can read and delete every note. Fine for localhost, worth remembering before
this gets exposed anywhere.
