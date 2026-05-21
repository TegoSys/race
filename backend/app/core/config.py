import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "race_agent")

# Absolute path to the raw files directory
STORAGE_PATH = str(BASE_DIR / "data" / "raw_files")

