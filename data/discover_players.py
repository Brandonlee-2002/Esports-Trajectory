# data/discover_players.py
from bs4 import BeautifulSoup
import re
from typing import List, Set

def discover_player_titles_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    titles: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        m = re.match(r"^/leagueoflegends/([^#?]+)$", href)
        if not m:
            continue

        title = m.group(1).replace("_", " ")

        # 🚫 drop namespaces and obvious non-player paths
        if ":" in title:
            continue
        if "/" in title:
            # players are almost always single-page titles; tournaments use /YEAR etc.
            continue
        if title.lower().startswith(("portal", "help", "special", "category")):
            continue

        titles.add(title)

    return sorted(titles)
