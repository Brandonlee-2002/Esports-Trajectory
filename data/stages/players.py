# data/stages/players.py
import sqlite3
import datetime as dt

from data.db import get_checkpoint, set_checkpoint
from data.discover_players import discover_player_titles_from_html
from data.cache import cache_get, cache_set
from data.scrape_player import parse_player_page
from data.mw import RateLimited


def _utc_now_str() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(sep=" ")


def _fetch_index_html(mw, index_page: str, cache_dir: str) -> str:
    """
    Fetch the Portal/Index HTML used to discover player titles.
    Cached under INDEX::<index_page>
    """
    key = f"INDEX::{index_page}"
    html = cache_get(cache_dir, key)
    if html:
        return html

    # Index/portal pages are easier to parse as full HTML
    html = mw.fetch_full_html(index_page)
    cache_set(cache_dir, key, html)
    return html


def _fetch_player_overview_html(mw, title: str, cache_dir: str) -> str:
    """
    Fetch a player's overview HTML (the page you see at /leagueoflegends/<Player>).
    Team history for LoL is inside the infobox "History" block on this page.

    Cached under PLAYER::<title>
    """
    key = f"PLAYER::{title}"
    html = cache_get(cache_dir, key)
    if html:
        return html

    # Use parse API (lighter than full page)
    html = mw.fetch_html(title)
    cache_set(cache_dir, key, html)
    return html


def run(conn: sqlite3.Connection, mw, cfg: dict) -> None:
    """
    Stage: discover player pages, scrape overview infobox history, insert players + team_stints.
    """
    index_page = cfg.get("player_index_page", "Portal:Players")
    cache_dir = cfg.get("cache_dir", ".cache_html")
    max_players = int(cfg.get("max_players", 0))

    print(f"[players] discovering players from index: {index_page}")

    # 1) Discover player titles from index page
    index_html = _fetch_index_html(mw, index_page, cache_dir)
    titles = discover_player_titles_from_html(index_html)

    if max_players > 0:
        titles = titles[:max_players]

    print(f"[players] discovered {len(titles)} player titles")
    print(f"[players] found {len(titles)} player pages (max={max_players or '∞'})")

    # 2) Resume from checkpoint
    done_key = "players:last_index"
    start_index = int(get_checkpoint(conn, done_key) or "0")

    # 3) Process each player
    for i in range(start_index, len(titles)):
        title = titles[i]
        url = mw.page_url(title)

        try:
            html = _fetch_player_overview_html(mw, title, cache_dir)
            profile, stints = parse_player_page(html, url)

        except RateLimited as e:
            print(f"[players] STOPPING due to rate limit: {e}")
            print("[players] resume later; checkpoint saved.")
            set_checkpoint(conn, done_key, str(i))  # retry same player next run
            return

        except Exception as e:
            print(f"[players] ERROR scraping {title}: {e}")
            set_checkpoint(conn, done_key, str(i + 1))
            continue

        now = _utc_now_str()

        # Insert/update player
        conn.execute(
            """
            INSERT INTO players(page_title, page_url, display_name, country, role, created_utc, updated_utc)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(page_title) DO UPDATE SET
              page_url=excluded.page_url,
              display_name=excluded.display_name,
              country=excluded.country,
              role=excluded.role,
              updated_utc=excluded.updated_utc
            """,
            (
                title,
                url,
                profile.get("display_name"),
                profile.get("country"),
                profile.get("role"),
                now,
                now,
            ),
        )

        # Insert stints (team history from infobox "History")
        for s in stints:
            conn.execute(
                """
                INSERT OR IGNORE INTO team_stints(
                  player_title, team, joined, left, note, source_url, created_utc
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    title,
                    s.get("team"),
                    s.get("joined"),
                    s.get("left"),
                    s.get("note"),
                    s.get("source_url"),
                    now,
                ),
            )

        conn.commit()
        set_checkpoint(conn, done_key, str(i + 1))

        if (i + 1) % 25 == 0:
            print(f"[players] processed {i+1}/{len(titles)}")

    print("[players] done.")
