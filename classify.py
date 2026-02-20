"""OpenRouter LLM 난이도 분류 모듈."""

import json
import time
from datetime import datetime, timezone

import httpx

from config import OPENROUTER_API_KEY
from db import init_db, get_unclassified_lines, upsert_quiz_line, get_difficulty_stats

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
BATCH_SIZE = 40

SYSTEM_PROMPT = """너는 MC THE MAX(엠씨더맥스) 전문가야. 가사 한 줄을 보고 퀴즈 난이도를 분류해야 해.

분류 기준:
- easy: 히트곡(어디에도, 잠시만 안녕, 그대가 분다, 하늘아래서, One Love, 넘쳐흘러 등)의 가장 유명한 후렴구/핵심 가사
- normal: 타이틀곡의 인식 가능한 가사 (후렴구는 아니지만 곡을 들으면 떠오르는 구절)
- hard: 비타이틀곡 가사 또는 타이틀곡이라도 특색 없는 구절 (일반적인 표현이 많은 경우)
- very_hard: 수록곡의 일반적인 표현으로 된 가사, 곡 특정이 매우 어려운 구절

각 가사에 대해 JSON 배열로 응답해. 형식: [{"id": 숫자, "difficulty": "easy|normal|hard|very_hard"}]
다른 설명 없이 JSON만 응답해."""


def classify_batch(lines: list[dict]) -> list[dict]:
    """가사 배치를 LLM으로 분류한다."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in .env")

    user_content = "\n".join(
        f'[{line["id"]}] ({line.get("title", "?")}) {line["line_text"]}'
        for line in lines
    )

    resp = httpx.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "google/gemini-3-flash-preview",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    text = data["choices"][0]["message"]["content"]
    # Extract JSON from potential markdown code block
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]

    return json.loads(text.strip())


def classify_all():
    """미분류 가사를 모두 분류한다."""
    init_db()

    # We need song titles for context, so join them
    from db import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT ll.*, s.title FROM lyrics_lines ll "
            "LEFT JOIN quiz_lines ql ON ll.id = ql.lyrics_line_id "
            "JOIN songs s ON ll.track_id = s.track_id "
            "WHERE ql.id IS NULL AND ll.char_count >= 5 "
            "ORDER BY ll.id"
        ).fetchall()
        unclassified = [dict(r) for r in rows]

    total = len(unclassified)
    if total == 0:
        print("All lines already classified!")
        return

    print(f"Classifying {total} lines in batches of {BATCH_SIZE}...")
    now = datetime.now(timezone.utc).isoformat()
    classified = 0

    for i in range(0, total, BATCH_SIZE):
        batch = unclassified[i:i + BATCH_SIZE]
        print(f"  Batch {i // BATCH_SIZE + 1} ({len(batch)} lines)...")

        try:
            results = classify_batch(batch)
            for r in results:
                if r.get("difficulty") in ("easy", "normal", "hard", "very_hard"):
                    upsert_quiz_line(r["id"], r["difficulty"], now)
                    classified += 1
        except Exception as e:
            print(f"    Error: {e}")
            continue

        time.sleep(1)

    print(f"\nClassified {classified}/{total} lines.")
    stats = get_difficulty_stats()
    for diff, cnt in sorted(stats.items()):
        print(f"  {diff}: {cnt}")


if __name__ == "__main__":
    classify_all()
