"""
Minimal WSGI app for Google App Engine (stdlib only).

Static HTML/CSS/JS are served by app.yaml. This only satisfies the runtime
requirement and handles infra paths like /_ah/warmup.
"""


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")

    if path == "/_ah/warmup":
        start_response("204 No Content", [])
        return [b""]

    if path == "/health":
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ok"]

    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]
