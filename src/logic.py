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

def get_secret(key: str):
    """Try Streamlit secrets first, fallback to .env"""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # Happens locally when no secrets.toml exists
        pass
    return os.getenv(key)

# --- Supabase setup ---
SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")

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


def save_predictions_db(username, matchday_number, predictions):
    """Save user predictions into Supabase, replacing old ones if they exist."""
    print("Saving predictions")
    print(username)
    print(matchday_number)
    print(predictions)
    timestamp = datetime.utcnow().isoformat()
 

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
    """Return % distribution of '1', 'X', '2' for a given match, directly from Supabase."""
    try:
        # ✅ Fetch only relevant rows
        res = (
            supabase.table("predictions")
            .select("prediction")
            .eq("home_team", home_team)
            .eq("away_team", away_team)
            .execute()
        )

        data = res.data or []
        if not data:
            return pd.Series({"1": 0, "X": 0, "2": 0})

        # ✅ Build DataFrame for aggregation
        df = pd.DataFrame(data)
        dist = df["prediction"].value_counts(normalize=True)
        return dist.reindex(["1", "X", "2"], fill_value=0)

    except Exception as e:
        print(f"⚠️ Error in get_prediction_distribution: {e}")
        return pd.Series({"1": 0, "X": 0, "2": 0})



def get_match_predictions(home_team, away_team):
    """Return a dict showing which users picked each prediction (1, X, 2) directly from Supabase."""
    try:
        # ✅ Fetch only the relevant columns for this match
        res = (
            supabase.table("predictions")
            .select("username, prediction")
            .eq("home_team", home_team)
            .eq("away_team", away_team)
            .execute()
        )

        data = res.data or []
        if not data:
            return {"1": [], "X": [], "2": []}

        # ✅ Build DataFrame for grouping
        df = pd.DataFrame(data)

        # ✅ Group usernames by prediction
        grouped = df.groupby("prediction")["username"].apply(list).to_dict()

        # ✅ Ensure all possible options are included
        return {opt: grouped.get(opt, []) for opt in ["1", "X", "2"]}

    except Exception as e:
        print(f"⚠️ Error in get_match_predictions: {e}")
        return {"1": [], "X": [], "2": []}



def get_number_of_users(matchday_number):
    """Return number of unique users who made predictions for a given jornada."""
    print(matchday_number)
    try:
        res = (
            supabase.table("predictions")
            .select("username")
            .eq("jornada", matchday_number)
            .execute()
        )

        data = res.data or []
        if not data:
            return 0

        df = pd.DataFrame(data)
        return df["username"].nunique()

    except Exception as e:
        print(f"⚠️ Error in get_number_of_users: {e}")
        return 0


def get_matchday():
    """Find the next jornada (matchday) after today, using Supabase filter."""
    today = datetime.today().strftime("%Y-%m-%d")
    try:
        # Query directly in Supabase
        res = (
            supabase.table("matchdays")
            .select("number, date")
            .gt("date", today)             # <-- Compare date column > today
            .order("date", desc=False)  # <-- Sort soonest first
            .limit(1)                       # <-- Get only the next jornada
            .execute()
        )

        data = res.data or []
        if not data:
            print("⚠️ No upcoming jornadas.")
            return None

        next_jornada = data[0]
        return next_jornada

    except Exception as e:
        print(f"⚠️ Error in get_next_jornada: {e}")
        return None

def get_matches(matchday: str):
    """
    Return all matches for a given matchday where result is NULL.
    Includes home_team, away_team, and their logos via join with 'teams' table.
    """
    print(matchday)
    try:
        home_teams = {t["name"]: t["logo"] for t in supabase.table("teams").select("name,logo").execute().data}
        away_teams = home_teams  # same table

        matches = supabase.table("results").select("*").eq("matchday", matchday).is_("result", None).execute().data

        formatted = []
        for m in matches:
            formatted.append({
                "home_team": m["home_team"],
                "home_logo": home_teams.get(m["home_team"]),
                "away_team": m["away_team"],
                "away_logo": away_teams.get(m["away_team"]),
                "result": m["result"],
            })


        return formatted

    except Exception as e:
        print(f"⚠️ Error in get_matches: {e}")
        return []


def get_existing_users():
    """Return a static sorted list of users."""
    users = sorted([
        "Adri", "Aaron", "Alvaro", "Jorge", "Quinco", "Callau",
        "Torrema", "Rovira", "Gorka", "Joan", "Guille", "Sergio",
        "Gimeno", "Chete", "Javi", "Luca"
    ])
    return users



# --- Corrected get_classification function ---
def get_classification():
    """
    Return the current classification table with team photos.
    This version manually joins classification with teams data in Python
    by matching 'name' columns, since 'team_id' does not exist.
    """
    try:
        # Fetch classification data
        # 'team_id' removed from select, as it does not exist.
        classification_data = supabase.table("classification").select(
            "name, position, avg_points, total_points, games_played, home_points_ratio, away_points_ratio, avg_goals_favor, avg_goals_against"
        ).order("position").execute().data

        # Fetch team data to get photo URLs
        teams_data = supabase.table("teams").select("name, logo").execute().data # Selecting 'name' for join key

        # Convert teams data to a dictionary for efficient lookup, using 'name' as the key
        team_photo_map = {team["name"]: team["logo"] for team in teams_data} # Using 'name' as key, directly storing logo

        processed_classification = []
        for item in classification_data:
            team_name = item.get("name") # Get the team's name from classification
            if team_name and team_name in team_photo_map:
                item['logo'] = team_photo_map[team_name] # Get logo using team_name
            else:
                item['logo'] = None # No photo if team name not found in teams data
            processed_classification.append(item)
            
        return processed_classification
    except Exception as e:
        print(f"⚠️ Error in get_classification: {e}")
        return []
    

def get_top_users():
    """
    Get users with the most correct predictions.
    Returns a list of dicts: [{"username": ..., "hits": ...}]
    """
    try:
        # Fetch all predictions (using 'jornada')
        predictions = supabase.table("predictions").select(
            "username, jornada, home_team, away_team, prediction"
        ).execute().data

        # Fetch all results (using 'matchday')
        results = supabase.table("results").select(
            "matchday, home_team, away_team, result"
        ).execute().data

        # Map results by their unique identifiers
        result_map = {
            (r["matchday"], r["home_team"], r["away_team"]): r["result"]
            for r in results if r.get("result")
        }

        # Count correct predictions
        hits = {}
        for p in predictions:
            # Normalize jornada → matchday for comparison
            key = (p["jornada"], p["home_team"], p["away_team"])
            # Compare against results table using jornada/matchday equivalence
            if key in result_map and p["prediction"] == result_map[key]:
                hits[p["username"]] = hits.get(p["username"], 0) + 1

        # Sort users by number of hits
        top_users = sorted(
            [{"username": u, "hits": c} for u, c in hits.items()],
            key=lambda x: x["hits"],
            reverse=True
        )

        return top_users

    except Exception as e:
        print(f"⚠️ Error in get_top_users: {e}")
        return []



def get_last_matchday():
    """Find the next jornada (matchday) after today, using Supabase filter."""
    today = datetime.today().strftime("%Y-%m-%d")
    try:
        # Query directly in Supabase
        res = (
            supabase.table("matchdays")
            .select("number, date")
            .lte("date", today)             # <-- Compare date column < today
            .order("date", desc=True)       # <-- Sort soonest first
            .limit(1)                       # <-- Get only the last matchday
            .execute()
        )

        data = res.data or []
        if not data:
            print("⚠️ No upcoming jornadas.")
            return None

        next_jornada = data[0]
        return next_jornada

    except Exception as e:
        print(f"⚠️ Error in get_next_jornada: {e}")
        return None

# --- Corrected get_users_hits_last_matchday function ---
def get_users_hits_last_matchday():
    """
    Return users and their hit ratio for the latest matchday.
    """

    try:
        last_matchday = get_last_matchday()["number"]

        # --- Get predictions for the last matchday ---
        # IMPORTANT: Replace "matchday" with the actual column name in your predictions table
        # Based on error, it's NOT 'matchday'. Let's assume 'jornada_number' as an example.
        predictions = supabase.table("predictions").select(
            "username, jornada, home_team, away_team, prediction" # <-- FIX: Replaced 'matchday'
        ).eq("jornada", last_matchday).execute().data # <-- FIX: Replaced 'matchday'

        # --- Get results for the last matchday ---
        # IMPORTANT: Replace "matchday" with the actual column name in your results table
        # Based on error, it's NOT 'matchday'. Let's assume 'jornada_number' as an example.
        results = supabase.table("results").select(
            "matchday, home_team, away_team, result" # <-- FIX: Replaced 'matchday'
        ).eq("matchday", last_matchday).execute().data # <-- FIX: Replaced 'matchday'

        result_map = {
            (r["home_team"], r["away_team"]): r["result"] 
            for r in results if r["result"]
        }

        ratio = {}
        total_preds = {}
        for p in predictions:
            user = p["username"]
            key = (p["home_team"], p["away_team"])
            total_preds[user] = total_preds.get(user, 0) + 1
            if key in result_map and p["prediction"] == result_map[key]:
                ratio[user] = ratio.get(user, 0) + 1

        # Compute hit ratios
        hit_ratios = [
            {"username": u, "hit_ratio": round(ratio.get(u, 0)/total_preds[u], 2)}
            for u in total_preds
        ]
        return sorted(hit_ratios, key=lambda x: x["hit_ratio"], reverse=True)

    except Exception as e:
        print(f"⚠️ Error in get_users_hit_ratio_last_matchday: {e}")
        return []

def get_jackpot():
    """
    Return the current bote (jackpot), currently mocked as 0.
    """
    return 0

