import sqlite3

from data.config import load_config
from data.db import init_db
from data.mw import MediaWikiClient
from data.stages.players import run as run_players
from data.stages.careers import run as run_careers


def main() -> None:
    cfg = load_config("config.json")

    conn = sqlite3.connect(cfg["db_path"])
    conn.execute("PRAGMA foreign_keys=ON;")
    init_db(conn)

    mw = MediaWikiClient(
        api_url=cfg["mw_api"],
        wiki_base=cfg["wiki_base"],
        user_agent=cfg["user_agent"],
        timeout_s=int(cfg.get("request_timeout_s", 30)),
        throttle_s=float(cfg.get("throttle_s", 0.5)),
    )

    run_players(conn, mw, cfg)
    run_careers(conn)

    conn.close()


if __name__ == "__main__":
    main()
