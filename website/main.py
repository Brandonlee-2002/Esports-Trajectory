"""
Minimal WSGI app for Google App Engine.

app.yaml lists static handlers for efficiency, but all routes are also served
here so the site works when traffic reaches Gunicorn (some buildpack / default
service setups do not apply static handlers the same way).
"""

import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from google.cloud import firestore
except Exception:  # pragma: no cover - optional local dependency
    firestore = None

_ROOT = Path(__file__).resolve().parent
_FALLBACK_FINDING: Dict[str, Any] = {
    "title": "Tier 2 promotion is limited",
    "summary": (
        "In the current Tier-2 debut panel, only a minority of players later "
        "reach Tier 1. Promotions cluster in the first few seasons after debut."
    ),
    "value": "37.5%",
    "metric_label": "Tier 2 to Tier 1 promotion rate",
    "updated_at": None,
}


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


def _json_response(
    start_response, status: str, payload: Dict[str, Any], cache_control: str = "no-store"
):
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Cache-Control", cache_control),
        ("Content-Length", str(len(body))),
    ]
    start_response(status, headers)
    return [body]


def _load_featured_finding_from_firestore() -> Optional[Dict[str, Any]]:
    if firestore is None:
        return None

    collection = os.environ.get("FIRESTORE_FEATURED_COLLECTION", "dashboard")
    document = os.environ.get("FIRESTORE_FEATURED_DOC", "major_findings")
    client = firestore.Client()
    snap = client.collection(collection).document(document).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    return {
        "title": str(data.get("title") or _FALLBACK_FINDING["title"]),
        "summary": str(data.get("summary") or _FALLBACK_FINDING["summary"]),
        "value": str(data.get("value") or _FALLBACK_FINDING["value"]),
        "metric_label": str(data.get("metric_label") or _FALLBACK_FINDING["metric_label"]),
        "updated_at": data.get("updated_at"),
    }


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")

    if path == "/_ah/warmup":
        start_response("204 No Content", [])
        return [b""]

    if path == "/health":
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ok"]

    if path == "/api/featured-finding":
        try:
            finding = _load_featured_finding_from_firestore()
            if finding is not None:
                return _json_response(
                    start_response,
                    "200 OK",
                    {"source": "firestore", "finding": finding},
                    cache_control="public, max-age=60",
                )
            return _json_response(
                start_response,
                "200 OK",
                {"source": "fallback", "finding": _FALLBACK_FINDING},
                cache_control="public, max-age=60",
            )
        except Exception as exc:
            return _json_response(
                start_response,
                "200 OK",
                {
                    "source": "fallback",
                    "finding": _FALLBACK_FINDING,
                    "error": f"firestore_unavailable: {exc}",
                },
                cache_control="public, max-age=60",
            )

    filepath = _file_for_path(path)
    if filepath is not None:
        data = filepath.read_bytes()
        ctype = mimetypes.guess_type(str(filepath))[0] or "application/octet-stream"
        if ctype == "text/html":
            ctype = "text/html; charset=utf-8"
        elif ctype.startswith("text/"):
            ctype = f"{ctype}; charset=utf-8"
        headers = [("Content-Type", ctype)]
        # Avoid stale charts when static handlers fall through to this app (match short app.yaml figure TTL).
        fp = str(filepath).replace("\\", "/").lower()
        if fp.endswith(".png") and "/assets/figures/" in fp:
            headers.append(("Cache-Control", "public, max-age=300"))
        start_response("200 OK", headers)
        return [data]

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]
