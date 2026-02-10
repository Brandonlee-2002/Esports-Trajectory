# data/liquipedia.py
import time
import requests
from typing import List, Dict, Optional

DEFAULT_HEADERS = {"User-Agent": "Esports-Trajectory/1.0 (brandon@example.com)"}

class LiquipediaClient:
    """
    Minimal, configurable client for Liquipedia-style APIs.
    This client is intentionally generic:
      - you provide endpoint templates in config (so we don't hardcode one endpoint)
      - the client returns list[dict] rows that the stage code maps into DB columns

    Configurable endpoints:
      - matches_endpoint: e.g. "https://liquipedia.net/api/matches?start={start}&end={end}&limit={limit}&offset={offset}"
      - match_players_endpoint: e.g. "https://liquipedia.net/api/matches/{match_id}/players?limit={limit}"
    """
    def __init__(self, headers: Optional[dict] = None, throttle_s: float = 0.35, timeout_s: int = 60):
        self.session = requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)
        self.throttle_s = throttle_s
        self.timeout_s = timeout_s

    def _get_json(self, url: str, params: dict = None) -> dict:
        r = self.session.get(url, params=params or {}, timeout=self.timeout_s)
        r.raise_for_status()
        payload = r.json()
        time.sleep(self.throttle_s)
        return payload

    # Example generic helper to fetch matches using a templated endpoint
    def get_matches(self, endpoint_template: str, start: str, end: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        endpoint_template should be a format string using {start}, {end}, {limit}, {offset}
        Start/end should be strings like "YYYY-MM-DD HH:MM:SS" or ISO datetime depending on the API.
        Returns a list[dict] (raw JSON rows) — the caller maps fields to DB columns.
        """
        url = endpoint_template.format(start=start, end=end, limit=limit, offset=offset)
        payload = self._get_json(url)
        # Different Liquipedia endpoints return different shapes.
        # Common patterns:
        #  - {'data': [...]} or {'results': [...]} or {'matches': [...] } or top-level list.
        for candidate in ("data", "results", "matches", "items", "rows", None):
            if candidate is None:
                # if payload itself is a list
                if isinstance(payload, list):
                    return payload
                continue
            if candidate in payload and isinstance(payload[candidate], list):
                return payload[candidate]
        # fallback: if a top-level key contains a list, return that first list
        for v in payload.values() if isinstance(payload, dict) else []:
            if isinstance(v, list):
                return v
        # nothing found — return empty list (caller should handle)
        return []

    def get_match_players(self, endpoint_template: str, match_id: str, limit: int = 200, offset: int = 0) -> List[Dict]:
        url = endpoint_template.format(match_id=match_id, limit=limit, offset=offset)
        payload = self._get_json(url)
        for candidate in ("data", "results", "players", "items", None):
            if candidate is None:
                if isinstance(payload, list):
                    return payload
                continue
            if candidate in payload and isinstance(payload[candidate], list):
                return payload[candidate]
        for v in payload.values() if isinstance(payload, dict) else []:
            if isinstance(v, list):
                return v
        return []
