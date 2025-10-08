from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "futbolcalendar"
DATA_FILE = DATA_DIR / "futsal_calendar.json"
DB_FILE = DATA_DIR / "predictions.duckdb"
