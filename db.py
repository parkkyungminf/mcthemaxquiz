"""SQLite database schema and query functions."""

import sqlite3
from contextlib import contextmanager
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                track_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                album TEXT,
                scraped_at TEXT
            );
            CREATE TABLE IF NOT EXISTS lyrics_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id INTEGER NOT NULL,
                line_no INTEGER NOT NULL,
                line_text TEXT NOT NULL,
                chosung TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                FOREIGN KEY (track_id) REFERENCES songs(track_id),
                UNIQUE(track_id, line_no)
            );
            CREATE TABLE IF NOT EXISTS quiz_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lyrics_line_id INTEGER NOT NULL UNIQUE,
                difficulty TEXT NOT NULL CHECK(difficulty IN ('easy','normal','hard','very_hard')),
                classified_at TEXT,
                FOREIGN KEY (lyrics_line_id) REFERENCES lyrics_lines(id)
            );
        """)


# --- Song queries ---

def upsert_song(track_id: int, title: str, album: str | None, scraped_at: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO songs(track_id, title, album, scraped_at) VALUES(?,?,?,?) "
            "ON CONFLICT(track_id) DO UPDATE SET title=excluded.title, album=excluded.album, scraped_at=excluded.scraped_at",
            (track_id, title, album, scraped_at),
        )


def get_song(track_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM songs WHERE track_id=?", (track_id,)).fetchone()
        return dict(row) if row else None


def get_all_songs() -> list[dict]:
    with get_db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM songs ORDER BY title").fetchall()]


# --- Lyrics queries ---

def insert_lyrics_line(track_id: int, line_no: int, line_text: str, chosung: str, char_count: int):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO lyrics_lines(track_id, line_no, line_text, chosung, char_count) "
            "VALUES(?,?,?,?,?)",
            (track_id, line_no, line_text, chosung, char_count),
        )


def get_lyrics_for_song(track_id: int) -> list[dict]:
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM lyrics_lines WHERE track_id=? ORDER BY line_no", (track_id,)
        ).fetchall()]


def get_unclassified_lines(limit: int = 200) -> list[dict]:
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT ll.* FROM lyrics_lines ll "
            "LEFT JOIN quiz_lines ql ON ll.id = ql.lyrics_line_id "
            "WHERE ql.id IS NULL AND ll.char_count >= 5 "
            "ORDER BY ll.id LIMIT ?",
            (limit,),
        ).fetchall()]


# --- Quiz queries ---

def upsert_quiz_line(lyrics_line_id: int, difficulty: str, classified_at: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO quiz_lines(lyrics_line_id, difficulty, classified_at) VALUES(?,?,?) "
            "ON CONFLICT(lyrics_line_id) DO UPDATE SET difficulty=excluded.difficulty, classified_at=excluded.classified_at",
            (lyrics_line_id, difficulty, classified_at),
        )


def get_quiz_questions(difficulty: str, count: int = 10) -> list[dict]:
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT ql.id as quiz_id, ql.difficulty, ll.id as line_id, ll.line_text, ll.chosung, "
            "ll.char_count, s.title, s.track_id "
            "FROM quiz_lines ql "
            "JOIN lyrics_lines ll ON ql.lyrics_line_id = ll.id "
            "JOIN songs s ON ll.track_id = s.track_id "
            "WHERE ql.difficulty = ? "
            "ORDER BY RANDOM() LIMIT ?",
            (difficulty, count),
        ).fetchall()]


def get_quiz_questions_mixed(count: int = 10) -> list[dict]:
    """혼합 난이도: easy 2, normal 3, hard 3, very_hard 2."""
    questions = []
    distribution = [("easy", 2), ("normal", 3), ("hard", 3), ("very_hard", 2)]
    with get_db() as conn:
        for diff, n in distribution:
            rows = conn.execute(
                "SELECT ql.id as quiz_id, ql.difficulty, ll.id as line_id, ll.line_text, ll.chosung, "
                "ll.char_count, s.title, s.track_id "
                "FROM quiz_lines ql "
                "JOIN lyrics_lines ll ON ql.lyrics_line_id = ll.id "
                "JOIN songs s ON ll.track_id = s.track_id "
                "WHERE ql.difficulty = ? "
                "ORDER BY RANDOM() LIMIT ?",
                (diff, n),
            ).fetchall()
            questions.extend(dict(r) for r in rows)
    return questions


def get_quiz_question_by_id(quiz_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT ql.id as quiz_id, ql.difficulty, ll.id as line_id, ll.line_text, ll.chosung, "
            "ll.char_count, s.title, s.track_id "
            "FROM quiz_lines ql "
            "JOIN lyrics_lines ll ON ql.lyrics_line_id = ll.id "
            "JOIN songs s ON ll.track_id = s.track_id "
            "WHERE ql.id = ?",
            (quiz_id,),
        ).fetchone()
        return dict(row) if row else None


def get_difficulty_stats() -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT difficulty, COUNT(*) as cnt FROM quiz_lines GROUP BY difficulty"
        ).fetchall()
        return {r["difficulty"]: r["cnt"] for r in rows}


def get_total_songs() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]


def get_total_lines() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM lyrics_lines").fetchone()[0]


if __name__ == "__main__":
    init_db()
    print(f"DB initialized at {DB_PATH}")
    print(f"Songs: {get_total_songs()}, Lines: {get_total_lines()}")
