# data/mw.py
from __future__ import annotations

import time
import random
import requests
from typing import Dict, List, Optional

from collections import deque

class HourlyRateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps = deque()

    def wait_for_slot(self):
        now = time.time()
        # drop timestamps outside the window
        while self.timestamps and now - self.timestamps[0] >= self.window_seconds:
            self.timestamps.popleft()

        if len(self.timestamps) < self.max_requests:
            self.timestamps.append(now)
            return

        # need to wait until the oldest falls out of the window
        sleep_for = self.window_seconds - (now - self.timestamps[0]) + random.uniform(0.5, 3.0)
        sleep_for = max(1.0, sleep_for)
        print(f"[mw] hourly limit reached ({self.max_requests}/{self.window_seconds}s). sleeping {sleep_for:.0f}s")
        time.sleep(sleep_for)

        # after sleeping, record
        now = time.time()
        while self.timestamps and now - self.timestamps[0] >= self.window_seconds:
            self.timestamps.popleft()
        self.timestamps.append(now)


class RateLimited(Exception):
    pass

class MediaWikiClient:
    def __init__(
        self,
        api_url: str,
        wiki_base: str,
        user_agent: str,
        timeout_s: int = 30,
        throttle_s: float = 1.5,
        max_retries: int = 8,
    ) -> None:
        self.api_url = api_url
        self.wiki_base = wiki_base.rstrip("/")
        self.timeout_s = timeout_s
        self.throttle_s = throttle_s
        self.max_retries = max_retries
        
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self.limiter = HourlyRateLimiter(max_requests=60, window_seconds=3600)


    def _sleep_polite(self, extra: float = 0.0) -> None:
        time.sleep(self.throttle_s + extra + random.uniform(0.0, 2.5))

    def page_exists(self, title: str) -> bool:
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
        }
        payload = self._request(params)
        pages = payload.get("query", {}).get("pages", {})
        if not pages:
            return False
        page = next(iter(pages.values()))
        return "missing" not in page



    def _request(self, params: dict) -> dict:
        """
        MediaWiki API JSON request with retry/backoff on 429/5xx.

        Minimal fixes:
          - 429 cooldown is LONG (Liquipedia hard-blocks)
          - handle HTML "Rate Limited" body (not JSON)
          - keep last_status/preview so errors are actionable
        """
        backoff = 10.0
        last_exc = None
        last_status = None
        last_preview = None
        last_retry_after = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.limiter.wait_for_slot()
                r = self.session.get(self.api_url, params=params, timeout=self.timeout_s)
                last_status = r.status_code
                last_retry_after = r.headers.get("Retry-After")
                body = r.text or ""
                last_preview = body[:200].replace("\n", " ")

                # Liquipedia often returns an HTML page on rate limit
                is_rate_limited = (r.status_code == 429) or ("Rate Limited - Liquipedia" in body)

                if is_rate_limited:
                    # If Retry-After exists, use it, else aggressive cooldown
                    raise RateLimited(f"Liquipedia rate limited on API call: {params.get('action')}/{params.get('list') or params.get('page')}")
                    

                if 500 <= r.status_code < 600:
                    wait = min(max(backoff, 10.0), 60.0)
                    print(f"[mw] server {r.status_code}. backing off {wait:.0f}s")
                    self._sleep_polite(extra=wait)
                    backoff = min(backoff * 1.6, 120.0)
                    continue

                r.raise_for_status()

                # If we got HTML instead of JSON (can happen), treat as failure
                ctype = (r.headers.get("Content-Type") or "").lower()
                if "application/json" not in ctype:
                    raise RuntimeError(f"Expected JSON but got Content-Type={ctype}. preview={last_preview!r}")

                self._sleep_polite()
                payload = r.json()

                # MediaWiki error payload
                if isinstance(payload, dict) and "error" in payload:
                    raise RuntimeError(f"MediaWiki API error: {payload['error']}")

                return payload

            except RateLimited:
                raise
            except Exception as e:
                last_exc = e
                wait = min(max(backoff, 10.0), 60.0)
                print(f"[mw] exception: {e} (attempt {attempt}/{self.max_retries}) sleeping {wait:.0f}s")
                self._sleep_polite(extra=wait)
                backoff = min(backoff * 1.6, 180.0)

        raise RuntimeError(
            f"MediaWiki API request failed after retries. "
            f"last_status={last_status} retry_after={last_retry_after} preview={last_preview!r} last_exc={last_exc} params={params}"
        )

    def list_category_members(self, category_title: str, limit: int = 50) -> List[Dict]:
        out: List[Dict] = []
        cmcontinue = None

        # small warm-up pause helps if you just got unblocked
        self._sleep_polite(extra=1.0)

        while True:
            params = {
                "action": "query",
                "format": "json",
                "list": "categorymembers",
                "cmtitle": category_title,
                "cmlimit": min(limit, 50),  # keep it small
                "cmnamespace": 0,
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue

            payload = self._request(params)
            out.extend(payload.get("query", {}).get("categorymembers", []))

            cmcontinue = payload.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break

        return out

    def page_url(self, title: str) -> str:
        return f"{self.wiki_base}/{title.replace(' ', '_')}"

    def fetch_html(self, title: str) -> str:
        # use parse API instead of full page fetch (more rate-limit friendly)
        params = {
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "text",
            "redirects": 1,
        }
        payload = self._request(params)
        html = payload.get("parse", {}).get("text", {}).get("*", "")
        if not html:
            raise RuntimeError(f"Empty HTML from parse API for title={title!r}")
        return html
    
    def fetch_full_html(self, title_or_path: str) -> str:
        """
        Fetch full HTML from the site (not API).
        """
        import time, random

        # ✅ Define url ONCE, outside the loop
        url = self.page_url(title_or_path) if not title_or_path.startswith("http") else title_or_path

        backoff = 10.0
        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self.limiter.wait_for_slot()
                r = self.session.get(url, timeout=self.timeout_s)
                body = r.text or ""

                if r.status_code == 429 or "Rate Limited - Liquipedia" in body:
                    wait = min(max(backoff, 60.0), 180.0)
                    print(f"[mw] 429 on HTML. cooling down {wait:.0f}s (attempt {attempt}/{self.max_retries})")
                    time.sleep(wait + random.uniform(0, 10))
                    backoff = min(backoff * 1.6, 180.0)
                    continue

                r.raise_for_status()
                time.sleep(self.throttle_s + random.uniform(0.0, 0.6))
                return body

            except Exception as e:
                last_exc = e
                wait = min(max(backoff, 30.0), 120.0)
                print(f"[mw] HTML exception (attempt {attempt}/{self.max_retries}): {e}. sleeping {wait:.0f}s")
                time.sleep(wait)
                backoff = min(backoff * 1.6, 180.0)

        # ✅ url is now always defined here
        raise RuntimeError(f"HTML fetch failed after retries: {url}. last_exc={last_exc}")
    
    def fetch_html_cached(self, title: str, cache_get, cache_set, cache_dir: str) -> str:
        key = f"PLAYER::{title}"
        html = cache_get(cache_dir, key) if cache_get else None
        if html:
            return html
        html = self.fetch_html(title)
        if cache_set:
            cache_set(cache_dir, key, html)
        return html



