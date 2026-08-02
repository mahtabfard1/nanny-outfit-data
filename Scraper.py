import argparse
import csv
import re
import time
from pathlib import Path
from urllib import urljoin , urlparse

import requests
from bs4 import BeautifulSoup


BASE ="https://thenanny.divinenanny.nl/"
USER_AGENT = ("EducationalOutfitDataBot/1.0" 
              +"(+youtube-data-science-tutorial; contact : mahtabfard.infor@gmail.com)")

REQUEST_DELAY_SECONDS = 1.0

EPISODE_RE = re.compile(r"(S\d{2}E\d{2}) \s*-\s*(.+)")



def get(session: requests.Session , url :str) -> str | None:
    resp = session.get(url , timeout=15)
    time.sleep(REQUEST_DELAY_SECONDS)
    if resp.status_code != 200:
        print(f"[warn] status {resp.status_code} for {url}")
        return None
    return resp.text


def discover_character_pages(session :requests.Session) -> list[tuple[str , str]]:
    html = get(session , BASE + "/")
    soup = BeautifulSoup(html , "html.parser")
    chars = []
    seen = set()
    for a in soup.select("a [href*='/characters/']"):
        href =  a["href"]
        full = urljoin(BASE , href)
        path = urlparse(full).path
        parts = [p for p in path.split("/") if p ]
        if len(parts) ==2 and parts[0] =="characters" and full not in seen:
            seen.add(full)
            chars.append((a.get_text(strip=True) , full))
    return chars 

