"""
fetch_h2_roster_panel — Leaguepedia Cargo API for Hypothesis 2 roster / tier panel.

Uses Special:CargoExport (JSON); no HTML scraping.

Base URL:
  https://lol.fandom.com/wiki/Special:CargoExport

Exports:
  - Tournaments: league / split / year / region → league → tier mapping
  - PlayerRedirects + Players: alias → canonical ID, nationality, residency
  - ScoreboardPlayers: one row per player per game (paginate offset by 500)
  - TournamentPlayers: roster-level participation per tournament

Usage (from repo root or this folder):
  python scrapers/fetch_h2_roster_panel.py tournaments --out data/raw/cargo/tournaments.jsonl
  python scrapers/fetch_h2_roster_panel.py scoreboard --year 2016 --out data/raw/cargo/scoreboard_2016.jsonl
  python scrapers/fetch_h2_roster_panel.py tournament-players --out data/raw/cargo/tournament_players.jsonl
  python scrapers/fetch_h2_roster_panel.py players-identity --out-dir data/raw/cargo

Requirements:
  pip install requests

Notes:
  - Max limit per request is 500; this module paginates with offset until a short page.
  - Be polite: default delay between requests (see REQUEST_DELAY_SEC).
  - Verify field names on https://lol.fandom.com/wiki/Special:CargoTables/<TableName>
    if a query starts failing after wiki schema changes.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlencode

import requests

CARGO_EXPORT_URL = "https://lol.fandom.com/wiki/Special:CargoExport"
MAX_LIMIT = 500
REQUEST_DELAY_SEC = 1.5
TIMEOUT_SEC = 120

DEFAULT_HEADERS = {
    "User-Agent": (
        "EsportsTrajectoryResearch/1.0 "
        "(CS capstone; +https://github.com/Brandonlee-2002/Esports-Trajectory)"
    ),
    "Accept": "application/json, text/json, */*",
}


class CargoExportError(Exception):
    pass


def _parse_cargo_json(text: str) -> List[Dict[str, Any]]:
    """Cargo usually returns a JSON array of objects; handle minor variants."""
    text = text.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise CargoExportError(
            f"Invalid JSON from Cargo (first 200 chars): {text[:200]!r}"
        ) from e

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        # Some endpoints wrap rows
        for key in ("rows", "data", "records"):
            if key in data and isinstance(data[key], list):
                return [x for x in data[key] if isinstance(x, dict)]
    raise CargoExportError(f"Unexpected Cargo JSON shape: {type(data).__name__}")


def cargo_export_request(
    params: Dict[str, Any],
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """Single GET to Special:CargoExport; returns list of row dicts."""
    sess = session or requests.Session()
    q = {k: v for k, v in params.items() if v is not None and v != ""}
    if "format" not in q:
        q["format"] = "json"
    url = f"{CARGO_EXPORT_URL}?{urlencode(q)}"
    resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=TIMEOUT_SEC)
    if resp.status_code == 429:
        raise CargoExportError("HTTP 429 rate limited — increase REQUEST_DELAY_SEC and retry.")
    if resp.status_code != 200:
        raise CargoExportError(f"HTTP {resp.status_code}: {resp.text[:500]}")

    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "json" not in ctype and not resp.text.lstrip().startswith(("[", "{")):
        raise CargoExportError(
            f"Non-JSON response (Content-Type={ctype!r}): {resp.text[:300]!r}"
        )

    return _parse_cargo_json(resp.text)


def cargo_export_paginated(
    base_params: Dict[str, Any],
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> Iterator[List[Dict[str, Any]]]:
    """
    Paginate with limit=500 and increasing offset.
    Yields each page as a list of rows (not single rows).
    """
    sess = session or requests.Session()
    offset = 0
    total = 0
    while True:
        params = {**base_params, "limit": min(int(base_params.get("limit", MAX_LIMIT)), MAX_LIMIT), "offset": offset}
        rows = cargo_export_request(params, session=sess)
        if not rows:
            break
        yield rows
        total += len(rows)
        if max_rows is not None and total >= max_rows:
            break
        if len(rows) < MAX_LIMIT:
            break
        offset += MAX_LIMIT
        time.sleep(delay_sec)


def export_jsonl(
    base_params: Dict[str, Any],
    out_path: Path,
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """Stream all pages to a JSON Lines file; returns row count written."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for page in cargo_export_paginated(
            base_params, session=session, delay_sec=delay_sec, max_rows=max_rows
        ):
            for row in page:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
                if max_rows is not None and n >= max_rows:
                    return n
            time.sleep(delay_sec)
    return n


# --- Preset queries (Hypothesis 2 + panel building) ---


def export_tournaments(
    out_path: Path,
    year_min: int = 2016,
    extra_where: str = "",
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """
    Tournaments: Name, Region, League, Split, Year, IsQualifier — league/tier mapping.
    """
    where = f"Year>={year_min}"
    if extra_where:
        where = f"({where}) AND ({extra_where})"
    params = {
        "tables": "Tournaments",
        "fields": "Name,Region,League,Split,Year,IsQualifier,DateStart,DateEnd,TournamentLevel",
        "where": where,
        "order_by": "Year ASC, DateStart ASC",
    }
    return export_jsonl(params, out_path, session=session, delay_sec=delay_sec, max_rows=max_rows)


def export_scoreboard_players(
    out_path: Path,
    year: int,
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """
    ScoreboardPlayers: one row per player per game.

    ``Link`` is the player page name. ``Tournament`` is often null; ``GameId`` usually
    embeds the season year (e.g. ``GPL/2016 Season/...``), so we OR both LIKE filters.
    """
    y = int(year)
    where = f"(Tournament LIKE '%{y}%') OR (GameId LIKE '%{y}%')"
    params = {
        "tables": "ScoreboardPlayers",
        "fields": "Link,Role,Team,Tournament,GameId",
        "where": where,
        "order_by": "GameId ASC, Link ASC",
    }
    return export_jsonl(params, out_path, session=session, delay_sec=delay_sec, max_rows=max_rows)


def export_tournament_players(
    out_path: Path,
    extra_where: str = "",
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """
    TournamentPlayers: roster row per player per tournament.

    Cargo stores the tournament key as ``OverviewPage``; we alias it to ``Tournament``
    in the export JSON for readability. There is no ``IsStarter`` field on this table.
    """
    where = extra_where or "1=1"
    params = {
        "tables": "TournamentPlayers",
        "fields": "Player,Team,OverviewPage=Tournament,Role",
        "where": where,
        "order_by": "OverviewPage ASC, Player ASC",
    }
    return export_jsonl(params, out_path, session=session, delay_sec=delay_sec, max_rows=max_rows)


def export_player_redirects_join_players(
    out_path: Path,
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """
    PlayerRedirects joined to Players on canonical ID.
    Each row: an alternate name (AllName) resolved to player demographics.

    If this fails (schema/join differences), use export_players_only and
    export_player_redirects_only separately and merge on ID in pandas.
    """
    params = {
        "tables": "PlayerRedirects,Players",
        "join_on": "PlayerRedirects.ID=Players.ID",
        "fields": (
            "PlayerRedirects.AllName=AliasName,"
            "Players.ID=PlayerID,"
            "Players.Player=Player,"
            "Players.Name=Name,"
            "Players.NameFull=NameFull,"
            "Players.Country=Country,"
            "Players.NationalityPrimary=NationalityPrimary,"
            "Players.Residency=Residency"
        ),
        # Drop redirect rows with no matching Players row (Cargo can otherwise emit nulls)
        "where": "Players.ID IS NOT NULL",
        "order_by": "Players.ID ASC, PlayerRedirects.AllName ASC",
    }
    return export_jsonl(params, out_path, session=session, delay_sec=delay_sec, max_rows=max_rows)


def export_players_only(
    out_path: Path,
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """Full Players table slice (paginated) — canonical IDs and residency fields."""
    params = {
        "tables": "Players",
        "fields": (
            "ID,Player,Name,NameFull,Country,NationalityPrimary,Residency,"
            "ResidencyFormer,Role,OverviewPage"
        ),
        "where": "1=1",
        "order_by": "ID ASC",
    }
    return export_jsonl(params, out_path, session=session, delay_sec=delay_sec, max_rows=max_rows)


def export_player_redirects_only(
    out_path: Path,
    session: Optional[requests.Session] = None,
    delay_sec: float = REQUEST_DELAY_SEC,
    max_rows: Optional[int] = None,
) -> int:
    """PlayerRedirects only — typically AllName → ID (canonical page name)."""
    params = {
        "tables": "PlayerRedirects",
        "fields": "AllName,ID",
        "where": "1=1",
        "order_by": "ID ASC, AllName ASC",
    }
    return export_jsonl(params, out_path, session=session, delay_sec=delay_sec, max_rows=max_rows)


def export_players_identity_bundle(out_dir: Path, session: Optional[requests.Session] = None) -> None:
    """
    Writes:
      players_redirects_join.jsonl  (preferred)
      If join is unsupported, fall back to players.jsonl + player_redirects.jsonl
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    join_path = out_dir / "players_redirects_join.jsonl"
    try:
        n = export_player_redirects_join_players(join_path, session=session)
        print(f"Wrote {n} rows to {join_path} (join query)")
        return
    except CargoExportError as e:
        print(f"Join export failed ({e}); falling back to separate tables.", file=sys.stderr)

    n1 = export_players_only(out_dir / "players.jsonl", session=session)
    n2 = export_player_redirects_only(out_dir / "player_redirects.jsonl", session=session)
    print(f"Wrote {n1} rows to {out_dir / 'players.jsonl'}")
    print(f"Wrote {n2} rows to {out_dir / 'player_redirects.jsonl'}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Hypothesis 2 roster panel — Leaguepedia Cargo Export (JSON/JSONL)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("tournaments", help="Export Tournaments (Year >= --year-min)")
    t.add_argument("--out", type=Path, required=True)
    t.add_argument("--year-min", type=int, default=2016)
    t.add_argument("--extra-where", default="", help="Additional Cargo WHERE (ANDed)")
    t.add_argument("--max-rows", type=int, default=None)

    s = sub.add_parser("scoreboard", help="Export ScoreboardPlayers for one calendar year in Tournament name")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--year", type=int, required=True)
    s.add_argument("--max-rows", type=int, default=None)

    tp = sub.add_parser("tournament-players", help="Export TournamentPlayers (full table, paginated)")
    tp.add_argument("--out", type=Path, required=True)
    tp.add_argument("--extra-where", default="", help="Cargo WHERE clause (default all rows)")
    tp.add_argument("--max-rows", type=int, default=None)

    iden = sub.add_parser("players-identity", help="Export PlayerRedirects+Players (or fallback split files)")
    iden.add_argument("--out-dir", type=Path, required=True)

    dry = sub.add_parser("dry-run", help="Print one page of tournaments (no file write)")
    dry.add_argument("--year-min", type=int, default=2016)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    session = requests.Session()

    try:
        if args.command == "tournaments":
            n = export_tournaments(
                args.out,
                year_min=args.year_min,
                extra_where=args.extra_where or "",
                session=session,
                max_rows=args.max_rows,
            )
            print(f"Wrote {n} rows to {args.out}")
        elif args.command == "scoreboard":
            n = export_scoreboard_players(
                args.out, year=args.year, session=session, max_rows=args.max_rows
            )
            print(f"Wrote {n} rows to {args.out}")
        elif args.command == "tournament-players":
            n = export_tournament_players(
                args.out,
                extra_where=args.extra_where or "",
                session=session,
                max_rows=args.max_rows,
            )
            print(f"Wrote {n} rows to {args.out}")
        elif args.command == "players-identity":
            export_players_identity_bundle(args.out_dir, session=session)
        elif args.command == "dry-run":
            params = {
                "tables": "Tournaments",
                "fields": "Name,League,Year,Split",
                "where": f"Year>={args.year_min}",
                "format": "json",
                "limit": 5,
            }
            rows = cargo_export_request(params, session=session)
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            raise SystemExit(2)
    except CargoExportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
