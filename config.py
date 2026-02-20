import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = os.getenv("DB_DIR")
DB_PATH = Path(DB_DIR) / "quiz.db" if DB_DIR else BASE_DIR / "data" / "quiz.db"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

BUGS_ARTIST_ID = "32585"  # MC THE MAX
SCRAPE_DELAY = 1.5  # seconds between requests
QUIZ_QUESTION_COUNT = 10
MAX_SCORE_PER_QUESTION = 100
