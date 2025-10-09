from pathlib import Path
from supabase import create_client, Client
import json
import pandas as pd
import os
import streamlit as st
from datetime import datetime

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "futbolcalendar"
DATA_FILE = DATA_DIR / "futsal_calendar.json"

def get_secret(key: str):
    """Try Streamlit secrets first, fallback to .env"""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # Happens locally when no secrets.toml exists
        pass
    return os.getenv(key)


def update_matchdays(data, supabase):
    """Insert or update matchdays with proper date type."""
    matchdays = []

    for jornada in data:
        # Parse date string into Python date object (expected format: DD-MM-YYYY)
        try:
            date_obj = datetime.strptime(jornada["date"], "%d-%m-%Y").date()
        except ValueError:
            print(f"⚠️ Invalid date format in jornada: {jornada['date']}")
            continue

        matchdays.append({
            "number": "".join([c for c in jornada["jornada"] if c.isdigit()]),
            "date": date_obj.isoformat()  # Send as ISO string (YYYY-MM-DD)
        })

    # Upsert each jornada
    for m in matchdays:
        supabase.table("matchdays").upsert(m, on_conflict="number").execute()

    print(f"✅ Matchdays table updated with {len(matchdays)} jornadas.")


def update_teams_table(data, supabase):
    # --- TEAMS ---
    teams = {}
    for jornada in data:
        for match in jornada["matches"]:
            teams[match["home_team"]] = match["home_logo"]
            teams[match["away_team"]] = match["away_logo"]

    for name, logo in teams.items():
        supabase.table("teams").upsert({"name": name, "logo": logo}, on_conflict="name").execute()

    print(f"✅ Teams table updated with {len(teams)} teams.")


def update_results_table(data, supabase):
    # --- RESULTS ---
    results = []
    for jornada in data:
        for match in jornada["matches"]:
            res = None
            if match.get("home_score") is not None and match.get("away_score") is not None:
                if match["home_score"] > match["away_score"]:
                    res = "1"
                elif match["home_score"] == match["away_score"]:
                    res = "X"
                else:
                    res = "2"
            results.append({
                "matchday": "".join([c for c in jornada["jornada"] if c.isdigit()]),
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "result": res
            })

    # Optional: remove old results
    supabase.table("results").delete().neq("home_team", "").execute()

    # Insert new results
    supabase.table("results").insert(results).execute()

    print(f"✅ Results table updated with {len(results)} matches.")



def update_classification_table(data, supabase: Client):
    """
    Compute and update the classification table in Supabase from the JSON data.
    
    Parameters:
        data (list): List of jornadas with match results.
        supabase (Client): Supabase client instance.
    """

    # --- Extract results from data ---
    results = []
    teams = {}  # Track all teams for initialization
    for jornada in data:
        for match in jornada["matches"]:
            home_score = match.get("home_score")
            away_score = match.get("away_score")

            # Add team to dict (for classification initialization)
            teams[match["home_team"]] = match.get("home_logo")
            teams[match["away_team"]] = match.get("away_logo")

            # Only compute result if scores exist
            if home_score is not None and away_score is not None:
                # Convert scores to int if strings
                home_score = int(home_score)
                away_score = int(away_score)

                if home_score > away_score:
                    result = "1"
                elif home_score == away_score:
                    result = "X"
                else:
                    result = "2"
            else:
                result = None

            results.append({
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "result": result,
                "home_goals": home_score,
                "away_goals": away_score
            })

    # --- Create DataFrame for results ---
    df_results = pd.DataFrame(results)
    df_results_played = df_results.dropna(subset=["home_goals", "away_goals"])

    # --- Initialize stats per team ---
    teams_stats = {
        team: {
            "name": team,
            "home_points_ratio": 0,
            "away_points_ratio": 0,
            "avg_goals_favor": 0,
            "avg_goals_against": 0,
            "played_home": 0,
            "played_away": 0,
            "total_goals_favor": 0,
            "total_goals_against": 0
        }
        for team in teams.keys()
    }

    # --- Compute stats ---
    for _, row in df_results_played.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        home_goals = row["home_goals"]
        away_goals = row["away_goals"]

        # Points
        if home_goals > away_goals:
            home_points, away_points = 3, 0
        elif home_goals == away_goals:
            home_points, away_points = 1, 1
        else:
            home_points, away_points = 0, 3

        # Update home stats
        teams_stats[home_team]["home_points_ratio"] += home_points
        teams_stats[home_team]["played_home"] += 1
        teams_stats[home_team]["total_goals_favor"] += home_goals
        teams_stats[home_team]["total_goals_against"] += away_goals

        # Update away stats
        teams_stats[away_team]["away_points_ratio"] += away_points
        teams_stats[away_team]["played_away"] += 1
        teams_stats[away_team]["total_goals_favor"] += away_goals
        teams_stats[away_team]["total_goals_against"] += home_goals

    # --- Compute averages ---
    classification_records = []
    for stats in teams_stats.values():
        played_home = stats["played_home"]
        played_away = stats["played_away"]
        played_total = played_home + played_away

        record = {
            "name": stats["name"],
            "home_points_ratio": round(stats["home_points_ratio"] / played_home, 2) if played_home > 0 else 0,
            "away_points_ratio": round(stats["away_points_ratio"] / played_away, 2) if played_away > 0 else 0,
            "avg_goals_favor": round(stats["total_goals_favor"] / max(played_total, 1), 2),
            "avg_goals_against": round(stats["total_goals_against"] / max(played_total, 1), 2)
        }
        classification_records.append(record)

    # --- Sort by total points descending ---
    classification_records.sort(key=lambda x: (x["home_points_ratio"] + x["away_points_ratio"]), reverse=True)
    for i, record in enumerate(classification_records, 1):
        record["position"] = i

    # --- Upsert into Supabase ---
    for rec in classification_records:
        supabase.table("classification").upsert(rec, on_conflict="name").execute()

    print(f"✅ Classification table updated with {len(classification_records)} teams.")


def update_data():
    """Create tables and insert/update teams, results, and classification from JSON."""
    if not DATA_FILE.exists():
        print("⚠️ JSON data file not found!")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Supabase setup ---
    SUPABASE_URL = get_secret("SUPABASE_URL")
    SUPABASE_KEY = get_secret("SUPABASE_KEY")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    update_matchdays(data, supabase)

    update_teams_table(data, supabase)

    update_results_table(data, supabase)

    update_classification_table(data, supabase)