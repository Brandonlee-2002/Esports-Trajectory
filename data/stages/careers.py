import sqlite3
import datetime as dt


def _utc_today_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def run(conn: sqlite3.Connection) -> None:
    print("[careers] rebuilding player_careers ...")

    conn.execute("DELETE FROM player_careers")

    today = _utc_today_iso()
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(sep=" ")

    # Career end: use latest "left" date; if null, use today (still active)
    # Career start: earliest "joined"
    # NOTE: if a player has no parsable dates, they won't get a career row.
    conn.execute(
        """
        INSERT INTO player_careers(player_title, career_start, career_end, career_days, stints_count, updated_utc)
        SELECT
          player_title,
          MIN(joined) AS career_start,
          MAX(COALESCE(left, ?)) AS career_end,
          ROUND(julianday(MAX(COALESCE(left, ?))) - julianday(MIN(joined)), 1) AS career_days,
          COUNT(*) AS stints_count,
          ?
        FROM team_stints
        WHERE joined IS NOT NULL
        GROUP BY player_title
        """,
        (today, today, now_utc),
    )

    conn.commit()
    print("[careers] done.")
