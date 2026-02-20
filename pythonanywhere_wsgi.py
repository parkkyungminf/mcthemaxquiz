import sys
from pathlib import Path
project_dir = '/home/parkkyungmin2/mcthemaxquiz'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
from dotenv import load_dotenv
load_dotenv(Path(project_dir) / '.env')
from db import init_db
from app import app as application
init_db()
