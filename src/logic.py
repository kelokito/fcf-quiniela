import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st
from supabase import create_client, Client
from config import BASE_DIR, DATA_DIR, DATA_FILE
from dotenv import load_dotenv
load_dotenv()

# --- Supabase setup ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_KEY.")
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- Load local data ---
def load_data():
    """Load match data from JSON file."""
    if not DATA_FILE.exists():
        st.error("⚠️ No match data found. Please run the scraper first.")
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Database logic using Supabase ---
def init_db():
    """Ensure the 'predictions' table exists (no-op if already created)."""
    try:
        supabase.table("predictions").select("*").limit(1).execute()
    except Exception:
        st.error("⚠️ Ensure the 'predictions' table exists in Supabase.")
        st.stop()


def save_predictions_db(username, jornada, predictions):
    """Save user predictions into Supabase, replacing old ones if they exist."""
    print("Saving predictions")
    print(username)
    print(jornada)
    print(predictions)
    timestamp = datetime.utcnow().isoformat()

    matchday_number = "".join([c for c in jornada if c.isdigit()])

    # 1️⃣ Delete old predictions for this user + jornada
    supabase.table("predictions").delete().match({
        "username": username,
        "jornada": matchday_number
    }).execute()

    # 2️⃣ Insert new ones
    new_records = [
        {
            "username": username,
            "jornada": matchday_number,
            "timestamp": timestamp,
            "home_team": info["home_team"],
            "away_team": info["away_team"],
            "prediction": info["prediction"]
        }
        for info in predictions.values()
        if info["prediction"]
    ]
    print(new_records)

    if new_records:
        supabase.table("predictions").insert(new_records).execute()


def get_all_predictions():
    """Return all predictions as a pandas DataFrame."""
    res = supabase.table("predictions").select("*").order("timestamp", desc=True).execute()
    if not res.data:
        return pd.DataFrame(columns=["username", "jornada", "timestamp", "match", "prediction"])
    return pd.DataFrame(res.data)


def get_prediction_distribution(home_team, away_team):
    """Return % distribution of '1', 'X', '2' for a given match."""
    df = get_all_predictions()
    match_df = df[(df["home_team"] == home_team) & (df["away_team"] == away_team)]
    if match_df.empty:
        return pd.Series({"1": 0, "X": 0, "2": 0})
    dist = match_df["prediction"].value_counts(normalize=True)
    return dist.reindex(["1", "X", "2"], fill_value=0)


def get_match_predictions(home_team, away_team):
    """Return a dict showing which users picked each prediction (1, X, 2)."""
    df = get_all_predictions()

    # ✅ Correct parenthesis for multiple conditions in Pandas
    match_df = df[(df["home_team"] == home_team) & (df["away_team"] == away_team)]

    if match_df.empty:
        return {"1": [], "X": [], "2": []}

    # ✅ Group users by prediction value
    grouped = match_df.groupby("prediction")["username"].apply(list).to_dict()

    # ✅ Ensure all possible outcomes exist
    return {opt: grouped.get(opt, []) for opt in ["1", "X", "2"]}



def get_number_of_users():
    """Return number of unique users who made predictions."""
    df = get_all_predictions()
    return df["username"].nunique()


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


def get_existing_users():
    """Return a static sorted list of users."""
    users = sorted([
        "Adri", "Aaron", "Alvaro", "Jorge", "Quinco", "Callau",
        "Torrema", "Rovira", "Gorka", "Joan", "Guille", "Sergio",
        "Gimeno", "Chete", "Javi", "Luca"
    ])
    return users
