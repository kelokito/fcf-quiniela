import json
import duckdb
from datetime import datetime
from pathlib import Path
import streamlit as st

from config import BASE_DIR, DATA_DIR, DATA_FILE, DB_FILE


def load_data():
    """Load match data from JSON file."""
    if not DATA_FILE.exists():
        st.error("⚠️ No match data found. Please run the scraper first.")
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def init_db():
    """Initialize DuckDB database and create predictions table if not exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_FILE))
    con.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            username TEXT,
            jornada TEXT,
            timestamp TIMESTAMP,
            match TEXT,
            prediction TEXT
        )
    """)
    return con


def save_predictions_db(username, jornada, predictions):
    """Save user predictions into the database."""
    con = init_db()
    timestamp = datetime.now()
    for match, pred in predictions.items():
        con.execute(
            "INSERT INTO predictions VALUES (?, ?, ?, ?, ?)",
            [username, jornada, timestamp, match, pred]
        )
    con.close()


def get_next_jornada(data):
    """Find the next jornada after today."""
    today = datetime.today()
    upcoming = []
    for jornada in data:
        try:
            date = datetime.strptime(jornada["date"], "%d-%m-%Y")
            if date >= today:
                upcoming.append((date, jornada))
        except Exception:
            continue

    if not upcoming:
        return data[-1]
    upcoming.sort(key=lambda x: x[0])
    return upcoming[0][1]


# --- New helper functions for statistics ---

def get_all_predictions():
    """Return all predictions as a pandas DataFrame."""
    con = init_db()
    df = con.execute("SELECT * FROM predictions ORDER BY timestamp DESC").df()
    con.close()
    return df


def get_prediction_distribution(match_name):
    """Return % distribution of '1', 'X', '2' for a given match."""
    df = get_all_predictions()
    match_df = df[df['match'] == match_name]
    if match_df.empty:
        return pd.Series({"1": 0, "X": 0, "2": 0})
    dist = match_df['prediction'].value_counts(normalize=True)
    return dist.reindex(["1", "X", "2"], fill_value=0)


def get_number_of_users():
    """Return number of unique users who made predictions."""
    df = get_all_predictions()
    return df['username'].nunique()
