# data/cache.py
import os
import hashlib

def _key(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def cache_get(cache_dir: str, key: str) -> str | None:
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, _key(key) + ".html")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

def cache_set(cache_dir: str, key: str, value: str) -> None:
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, _key(key) + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(value)
