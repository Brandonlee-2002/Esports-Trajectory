import sqlite3
import datetime as dt

SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_utc TEXT
);

CREATE TABLE IF NOT EXISTS players (
  page_title TEXT PRIMARY KEY,
  page_url TEXT,
  display_name TEXT,
  country TEXT,
  role TEXT,
  created_utc TEXT,
  updated_utc TEXT
);

CREATE TABLE IF NOT EXISTS team_stints (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  player_title TEXT NOT NULL,
  team TEXT,
  joined TEXT,
  left TEXT,
  note TEXT,
  source_url TEXT,
  created_utc TEXT,
  UNIQUE(player_title, team, joined, left, note),
  FOREIGN KEY(player_title) REFERENCES players(page_title) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS player_careers (
  player_title TEXT PRIMARY KEY,
  career_start TEXT,
  career_end TEXT,
  career_days REAL,
  stints_count INTEGER,
  updated_utc TEXT,
  FOREIGN KEY(player_title) REFERENCES players(page_title) ON DELETE CASCADE
);
"""


def _utc_now_str() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(sep=" ")


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def get_checkpoint(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM checkpoints WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def set_checkpoint(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO checkpoints(key, value, updated_utc) VALUES (?,?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_utc=excluded.updated_utc
        """,
        (key, value, _utc_now_str()),
    )
    conn.commit()
