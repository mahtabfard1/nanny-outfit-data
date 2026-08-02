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
    for a in soup.select("a[href*='/characters/']"):
        href =  a["href"]
        full = urljoin(BASE , href)
        path = urlparse(full).path
        parts = [p for p in path.split("/") if p ]
        if len(parts) ==2 and parts[0] =="characters" and full not in seen:
            seen.add(full)
            chars.append((a.get_text(strip=True) , full))
    return chars 

def discover_season_pages(session : requests.Session , season_url: str , character_url :str):
    html = get(session , character_url)
    if not html:
        return[]
    soup = BeautifulSoup(html , "html.parser")
    season_url = set()
    char_path = urlparse(character_url).path.rstrip("/")
    for a in soup.select("a[href]"):
        full = urljoin(BASE , a["href"])
        path = urlparse(full).path.rstrip("/")
        if path.startswith(char_path + "/") and path != char_path:
            season_url.add(full)
    return sorted(season_url)
def parse_season_page(session : requests.Session , season_url: str , character: str):
    html = get(session , season_url)
    if not html:
        return[]
    soup = BeautifulSoup(html , "html.parser")
    
    #season number from the page title e.g "Gracie - Season 4"
    
    title = soup.find("h1")
    season_label = title.get_text(strip = True) if title else ""
    m = re.search(r"Season\s*(\d+)" , season_label)
    season_num = int(m.group(1)) if m else None
    
    rows = []
    current_episode_code , current_episode_title = None , None
    
    for tag in soup.find_all(["h2" , "img"]):
        if tag.name =="h2":
            text = tag.get_text(" " , strip = True).replace("#" , "") .strip()
            m=EPISODE_RE.match(text)
            if m:
                current_episode_code , current_episode_title = m.group(1) , m.group(2).strip()
            else:
                current_episode_code , current_episode_title = None , text
        elif tag.name == "img" and current_episode_code:
            src = tag.get("src" , "")
            if not src:
                continue
            img_url = urljoin(BASE , src)
            rows.append({
                "character" : character,
                "season" : season_num , 
                "episode_code" : current_episode_code,
                "episode_title" : current_episode_title,
                "image_url" : img_url,
            })
    return rows

def download_image(session: requests.Session , url : str , dest:Path):
    if dest.exists():
        return
    resp = session.get(url , timeout = 15)
    time.sleep(REQUEST_DELAY_SECONDS)
    if resp.status_code == 200:
        dest.parent.mkdir(parents=True , exist_ok=True)
        dest.write_bytes(resp.content)
    else:
        print(f"[warn] could not download{url} (status{resp.status_code})")
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out" , default="outfit.csv")
    parser.add_argument("--download-images" , action="store_true" , help="Also download each outfit image into ./images/")
    parser.add_argument("--images-dir" , default="images")
    args = parser.parse_args()
    
    session =requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    
    print("Discovering character pages ....")
    characters = discover_character_pages(session)
    print(f"found {len(characters)} characters")
    
    all_rows=[]
    for name , char_url in characters:
        print(f"\nCharacter: {name} ({char_url})")
        season_urls = discover_season_pages(session , char_url)
        print(f"found {len(season_urls)} season pages")
        for season_url in season_urls:
            print(f" parsing {season_url}")
            rows = parse_season_page(session , season_url , name)
            all_rows.extend(rows)
    if not all_rows:
        print("No data scraped")
        return
    fieldnames = list(all_rows[0].keys())
    with open(args.out , "w" , newline="" , encoding="utf-8") as f:
        writer = csv.DictWriter(f , fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\nSaved {len(all_rows)} outfit-image rows to {args.out}")
    
    if args.download_images:
        print("\nDownloading images")
        img_dir = Path(args.images_dir)
        for i , row in enumerate(all_rows , 1):
            fname = f"{row['episode_code']}_{row['character']}_{i}.jpg".replace(" ", "_")
            download_image(session , row["image_url"] , img_dir / fname)
            if i % 20 ==0:
                print(f"{i} / {len(all_rows)} downloaded")
        print(f"Images saved to {img_dir}/")

if __name__ == "__main__":
    main()

