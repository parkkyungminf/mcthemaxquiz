"""MC THE MAX 초성퀴즈 Flask 웹앱."""

import hmac
import re
from difflib import SequenceMatcher
from functools import wraps

from flask import Flask, render_template, request, session, redirect, url_for, jsonify

from config import FLASK_SECRET_KEY, QUIZ_QUESTION_COUNT, ADMIN_TOKEN
from db import (
    init_db, get_quiz_questions, get_quiz_questions_mixed,
    get_quiz_question_by_id,
    get_difficulty_stats, get_total_songs, get_total_lines,
)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_TOKEN:
            return jsonify({"error": "admin not configured"}), 403
        token = request.headers.get("X-Admin-Token", "")
        if not token or not hmac.compare_digest(token, ADMIN_TOKEN):
            return jsonify({"error": "unauthorized"}), 403
        return f(*args, **kwargs)
    return decorated


def normalize_title(title: str) -> str:
    """곡명 비교를 위해 정규화 (괄호 안 버전 정보 제거, 소문자, 공백 제거)."""
    title = re.sub(r"\(.*?\)", "", title)  # remove parenthetical
    title = re.sub(r"[^\w가-힣]", "", title)  # keep only word chars + hangul
    return title.strip().lower()


def check_lyrics(answer: str, correct: str) -> tuple[int, str]:
    """가사 정답 체크. (점수, 판정)을 반환."""
    a = answer.strip()
    c = correct.strip()
    if a == c:
        return 50, "exact"
    if not a:
        return 0, "wrong"
    ratio = SequenceMatcher(None, a, c).ratio()
    if ratio >= 0.8:
        return 25, "partial"
    return 0, "wrong"


@app.route("/")
def index():
    stats = get_difficulty_stats()
    total_songs = get_total_songs()
    total_lines = get_total_lines()
    total_quiz = sum(stats.values())
    return render_template("index.html", stats=stats, total_songs=total_songs,
                           total_lines=total_lines, total_quiz=total_quiz)


@app.route("/quiz/start", methods=["POST"])
def quiz_start():
    difficulty = request.form.get("difficulty", "normal")

    if difficulty == "mixed":
        questions = get_quiz_questions_mixed(QUIZ_QUESTION_COUNT)
    else:
        questions = get_quiz_questions(difficulty, QUIZ_QUESTION_COUNT)

    if not questions:
        return redirect(url_for("index"))

    # Session stores only IDs + display info (no answers)
    session["quiz_ids"] = [q["quiz_id"] for q in questions]
    session["quiz_display"] = [
        {"chosung": q["chosung"], "char_count": q["char_count"], "difficulty": q["difficulty"]}
        for q in questions
    ]
    session["current"] = 0
    session["score"] = 0
    session["results"] = []
    session["difficulty"] = difficulty
    return redirect(url_for("quiz_question"))


@app.route("/quiz/question")
def quiz_question():
    quiz_ids = session.get("quiz_ids")
    display = session.get("quiz_display")
    current = session.get("current", 0)

    if not quiz_ids or current >= len(quiz_ids):
        return redirect(url_for("quiz_result"))

    q = display[current]
    return render_template("quiz.html", question=q, current=current + 1,
                           total=len(quiz_ids), score=session.get("score", 0))


@app.route("/quiz/answer", methods=["POST"])
def quiz_answer():
    quiz_ids = session.get("quiz_ids")
    current = session.get("current", 0)

    if not quiz_ids or current >= len(quiz_ids):
        return redirect(url_for("quiz_result"))

    # Fetch correct answer from DB (not from session)
    q = get_quiz_question_by_id(quiz_ids[current])
    if not q:
        return redirect(url_for("quiz_result"))

    title_answer = request.form.get("title", "").strip()
    lyrics_answer = request.form.get("lyrics", "").strip()

    # Score title
    title_score = 0
    title_match = "wrong"
    if normalize_title(title_answer) == normalize_title(q["title"]):
        title_score = 50
        title_match = "exact"

    # Score lyrics (2줄 합쳐서 비교, 줄바꿈 제거 후 비교)
    correct_lyrics = q["line_text"].replace("\n", " ")
    lyrics_score, lyrics_match = check_lyrics(lyrics_answer, correct_lyrics)

    total_q_score = title_score + lyrics_score

    result = {
        "question_no": current + 1,
        "chosung": q["chosung"],
        "correct_title": q["title"],
        "correct_lyrics": q["line_text"],
        "user_title": title_answer,
        "user_lyrics": lyrics_answer,
        "title_match": title_match,
        "lyrics_match": lyrics_match,
        "title_score": title_score,
        "lyrics_score": lyrics_score,
        "total_score": total_q_score,
        "difficulty": q.get("difficulty", ""),
    }

    session["score"] = session.get("score", 0) + total_q_score
    results = session.get("results", [])
    results.append(result)
    session["results"] = results
    session["current"] = current + 1

    # Return JSON for AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(result)

    return redirect(url_for("quiz_question"))


@app.route("/quiz/result")
def quiz_result():
    results = session.get("results", [])
    score = session.get("score", 0)
    total = len(results) * 100 if results else 1
    difficulty = session.get("difficulty", "")
    return render_template("result.html", results=results, score=score,
                           total=total, difficulty=difficulty)


@app.route("/admin/scrape", methods=["POST"])
@require_admin
def admin_scrape():
    from scraper import scrape_all
    result = scrape_all()
    return jsonify(result)


@app.route("/admin/classify", methods=["POST"])
@require_admin
def admin_classify():
    from classify import classify_all
    classify_all()
    stats = get_difficulty_stats()
    return jsonify(stats)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
