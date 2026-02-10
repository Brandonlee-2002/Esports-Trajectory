# data/scrape_player.py
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from dateutil import parser as dateparser


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _parse_date(s: str) -> Optional[str]:
    t = _clean(s)
    if not t:
        return None
    low = t.lower()
    if low in {"present", "current", "now", "ongoing", "-", "—"}:
        return None
    try:
        d = dateparser.parse(t, fuzzy=True)
        return d.date().isoformat() if d else None
    except Exception:
        return None


def _split_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    "2013-02-06 – 2014-12-02" -> (start, end)
    "2014-12-02 – Present" -> (start, None)
    """
    t = _clean(text)
    if not t:
        return None, None

    parts = re.split(r"\s*[–—-]\s*", t)
    if len(parts) == 1:
        return _parse_date(parts[0]), None
    start = _parse_date(parts[0])
    end = _parse_date(parts[1])
    return start, end


def _extract_infobox_history_stints(soup: BeautifulSoup, source_url: str) -> List[Dict]:
    """
    Liquipedia LoL infobox contains a "History" section with rows like:
      2013-02-06 – 2014-12-02   SK Telecom T1 K
      2014-12-02 – Present     T1
    We find the "History" header in the infobox and parse subsequent rows.
    """
    stints: List[Dict] = []

    # Infobox wrapper on Liquipedia (your HTML shows fo-nttax-infobox)
    infobox = soup.select_one(".fo-nttax-infobox") or soup.select_one(".infobox-leagueoflegends")
    if not infobox:
        return stints

    # Find the element whose text is "History"
    history_header = None
    for el in infobox.find_all(["div", "th", "td"], recursive=True):
        if _clean(el.get_text(" ", strip=True)).lower() == "history":
            history_header = el
            break

    if not history_header:
        return stints

    # The rows are typically in the next table after the header, but can vary.
    # Strategy:
    #  - Walk forward until we hit a table, then parse its rows
    table = history_header.find_parent("table")
    if table is None:
        table = history_header.find_next("table")

    if table is None:
        # Some infoboxes render "rows" as divs; fallback to sibling scanning
        container = history_header.find_parent()
        if not container:
            return stints
        # look at next siblings for date/team patterns
        sib = container.find_next_sibling()
        while sib:
            txt = _clean(sib.get_text(" ", strip=True))
            if not txt:
                sib = sib.find_next_sibling()
                continue
            # stop if we hit a new section header
            if txt.lower() in {"results", "achievements", "statistics"}:
                break
            sib = sib.find_next_sibling()
        return stints

    # Parse table rows: expect two columns (date range, team)
    for tr in table.find_all("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) < 2:
            continue

        left_txt = _clean(tds[0].get_text(" ", strip=True))
        right_txt = _clean(tds[1].get_text(" ", strip=True))

        # date range is usually left, team is right
        joined, left = _split_range(left_txt)

        # team might be a link; prefer link text if present
        team_a = tds[1].find("a")
        team = _clean(team_a.get_text(strip=True)) if team_a else right_txt

        if team and (joined or left_txt.lower().find("present") >= 0):
            stints.append(
                {
                    "team": team,
                    "joined": joined,
                    "left": left,
                    "note": None,
                    "source_url": source_url,
                }
            )

    return stints


def parse_player_page(html: str, page_url: str) -> Tuple[Dict, List[Dict]]:
    soup = BeautifulSoup(html, "lxml")

    profile = {"display_name": None, "country": None, "role": None}

    # Basic name best-effort
    h1 = soup.find("h1", id="firstHeading")
    if h1:
        profile["display_name"] = _clean(h1.get_text(strip=True))
    else:
        p = soup.find("p")
        if p and p.find("b"):
            profile["display_name"] = _clean(p.find("b").get_text(strip=True))

    # Stints from infobox History
    stints = _extract_infobox_history_stints(soup, page_url)

    return profile, stints
