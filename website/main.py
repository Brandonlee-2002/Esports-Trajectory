"""
Minimal WSGI app for Google App Engine (stdlib only).

app.yaml lists static handlers for efficiency, but all routes are also served
here so the site works when traffic reaches Gunicorn (some buildpack / default
service setups do not apply static handlers the same way).
"""

import mimetypes
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def _file_for_path(path: str):
    """Return a Path to a file under _ROOT, or None if not allowed / missing."""
    if not path or path == "/":
        candidate = _ROOT / "index.html"
        return candidate if candidate.is_file() else None

    rel = path.lstrip("/")
    if not rel:
        candidate = _ROOT / "index.html"
        return candidate if candidate.is_file() else None

    candidate = (_ROOT / rel).resolve()
    try:
        candidate.relative_to(_ROOT)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")

    if path == "/_ah/warmup":
        start_response("204 No Content", [])
        return [b""]

    if path == "/health":
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ok"]

    filepath = _file_for_path(path)
    if filepath is not None:
        data = filepath.read_bytes()
        ctype = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
        if ctype == "text/html":
            ctype = "text/html; charset=utf-8"
        elif ctype.startswith("text/"):
            ctype = f"{ctype}; charset=utf-8"
        start_response("200 OK", [("Content-Type", ctype)])
        return [data]

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]
