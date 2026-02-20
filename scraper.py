"""Bugs Music scraper for MC THE MAX tracks and lyrics."""

import io
import re
import sys
import time
from datetime import datetime, timezone

# Fix Windows console encoding for Korean text
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup

from chosung import extract_chosung, count_korean_chars
from config import BUGS_ARTIST_ID, SCRAPE_DELAY
from db import init_db, upsert_song, insert_lyrics_line, get_song, get_total_songs, get_total_lines

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://music.bugs.co.kr/",
}


def fetch_track_list(page: int = 1) -> list[dict]:
    """아티스트 트랙 목록 페이지를 가져온다."""
    url = f"https://music.bugs.co.kr/artist/{BUGS_ARTIST_ID}/tracks"
    params = {"page": page}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tracks = []
    for row in soup.select("table.list tbody tr"):
        title_el = row.select_one("p.title a")
        if not title_el:
            continue

        # track_id from onclick or href
        onclick = title_el.get("onclick", "")
        href = title_el.get("href", "")
        track_id = None

        # Try extracting from href like /track/6273241
        m = re.search(r"/track/(\d+)", href)
        if m:
            track_id = int(m.group(1))

        # Try extracting from onclick
        if not track_id:
            m = re.search(r"(\d{5,})", onclick)
            if m:
                track_id = int(m.group(1))

        if not track_id:
            continue

        title = title_el.get_text(strip=True)
        album_el = row.select_one("a.album")
        album = album_el.get_text(strip=True) if album_el else None

        tracks.append({"track_id": track_id, "title": title, "album": album})

    return tracks


def fetch_all_tracks() -> list[dict]:
    """모든 페이지의 트랙 목록을 가져온다."""
    all_tracks = []
    page = 1
    while True:
        print(f"  Fetching track list page {page}...")
        tracks = fetch_track_list(page)
        if not tracks:
            break
        all_tracks.extend(tracks)
        page += 1
        time.sleep(SCRAPE_DELAY)
    # deduplicate by track_id
    seen = set()
    unique = []
    for t in all_tracks:
        if t["track_id"] not in seen:
            seen.add(t["track_id"])
            unique.append(t)
    return unique


def fetch_lyrics(track_id: int) -> str | None:
    """트랙의 가사를 가져온다. 비시간동기화 → 시간동기화 폴백."""
    import json as _json
    for prefix in ("N", "T"):
        url = f"https://music.bugs.co.kr/player/lyrics/{prefix}/{track_id}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            body = resp.text.strip()
            if not body:
                continue

            # API returns JSON: {"lyrics":"...", "userId":"..."}
            try:
                data = _json.loads(body)
                text = data.get("lyrics", "")
            except _json.JSONDecodeError:
                text = body

            if not text:
                continue

            # Clean time-sync tags if present
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", text)
            # Normalize line breaks
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines:
                return "\n".join(lines)
        except requests.RequestException:
            continue
    return None


def scrape_all():
    """전체 크롤링을 실행한다."""
    init_db()
    now = datetime.now(timezone.utc).isoformat()

    print("Fetching track list...")
    tracks = fetch_all_tracks()
    print(f"Found {len(tracks)} unique tracks.")

    lyrics_count = 0
    for i, t in enumerate(tracks, 1):
        upsert_song(t["track_id"], t["title"], t["album"], now)

        if get_song(t["track_id"]):
            # Check if we already have lyrics
            from db import get_lyrics_for_song
            if get_lyrics_for_song(t["track_id"]):
                print(f"  [{i}/{len(tracks)}] {t['title']} - already has lyrics, skipping")
                continue

        print(f"  [{i}/{len(tracks)}] Fetching lyrics: {t['title']}...")
        lyrics = fetch_lyrics(t["track_id"])
        if not lyrics:
            print(f"    No lyrics found.")
            continue

        for line_no, line in enumerate(lyrics.split("\n"), 1):
            line = line.strip()
            if not line or count_korean_chars(line) < 2:
                continue
            chosung = extract_chosung(line)
            char_count = count_korean_chars(line)
            insert_lyrics_line(t["track_id"], line_no, line, chosung, char_count)
            lyrics_count += 1

        time.sleep(SCRAPE_DELAY)

    print(f"\nDone! Songs: {get_total_songs()}, Lyrics lines: {get_total_lines()}")
    return {"songs": get_total_songs(), "lines": get_total_lines()}


if __name__ == "__main__":
    scrape_all()
