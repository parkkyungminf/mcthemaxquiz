"""PythonAnywhere WSGI entrypoint."""

import sys
from pathlib import Path

project_dir = str(Path(__file__).resolve().parent)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from db import init_db
from app import app as application

init_db()
