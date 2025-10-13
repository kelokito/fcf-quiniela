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
    Now also includes 'avg_points'.
    
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
            "home_points": 0, # Renamed from home_points_ratio for clarity during accumulation
            "away_points": 0, # Renamed from away_points_ratio for clarity during accumulation
            "total_points": 0, # New: To accumulate total points
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
        teams_stats[home_team]["home_points"] += home_points
        teams_stats[home_team]["total_points"] += home_points # Accumulate total points
        teams_stats[home_team]["played_home"] += 1
        teams_stats[home_team]["total_goals_favor"] += home_goals
        teams_stats[home_team]["total_goals_against"] += away_goals

        # Update away stats
        teams_stats[away_team]["away_points"] += away_points
        teams_stats[away_team]["total_points"] += away_points # Accumulate total points
        teams_stats[away_team]["played_away"] += 1
        teams_stats[away_team]["total_goals_favor"] += away_goals
        teams_stats[away_team]["total_goals_against"] += home_goals

    # --- Compute averages ---
    classification_records = []
    for stats in teams_stats.values():
        played_home = stats["played_home"]
        played_away = stats["played_away"]
        played_total = played_home + played_away # Total games played by this team

        # Calculate avg_points
        total_points = stats["total_points"]
        avg_points = round(total_points / played_total, 2) if played_total > 0 else 0

        record = {
            "name": stats["name"],
            # These are now actual points accumulated, not ratios yet. Renamed for clarity in DB.
            #"home_points_total": stats["home_points"], # New field for total home points
            #"away_points_total": stats["away_points"], # New field for total away points
            "home_points_ratio": round(stats["home_points"] / played_home, 2) if played_home > 0 else 0,
            "away_points_ratio": round(stats["away_points"] / played_away, 2) if played_away > 0 else 0,
            "avg_goals_favor": round(stats["total_goals_favor"] / max(played_total, 1), 2),
            "avg_goals_against": round(stats["total_goals_against"] / max(played_total, 1), 2),
            "avg_points": avg_points, # New: Average points per game
            "total_points": stats["home_points"]+stats["away_points"],
            "games_played": stats["played_home"] + stats["played_away"]
        }
        classification_records.append(record)

    # --- Sort by total points descending ---
    # Now sorting by the newly calculated avg_points, or total_points if you prefer that for ranking
    classification_records.sort(key=lambda x: (-x["avg_points"], x["games_played"]))
    # Or, if you want to sort by total points:
    # classification_records.sort(key=lambda x: (x["home_points_total"] + x["away_points_total"]), reverse=True)


    for i, record in enumerate(classification_records, 1):
        record["position"] = i

    # --- Upsert into Supabase ---
    for rec in classification_records:
        supabase.table("classification").upsert(rec, on_conflict="name").execute()

    print(f"✅ Classification table updated with {len(classification_records)} teams.")


def update_last_refresh(supabase):
    """
    Insert a new record into the 'last_refresh' table with the current timestamp.
    """
    try:
        # Get the current UTC time in ISO format (you can use local time if you prefer)
        now = datetime.utcnow().isoformat()

        data = {"moment": now}

        # Insert into Supabase
        res = supabase.table("last_refresh").insert(data).execute()

        if res.data:
            print(f"✅ Last refresh updated at {now}")
        else:
            print("⚠️ Insert succeeded but returned no data.")

    except Exception as e:
        print(f"❌ Error in update_last_refresh: {e}")




def winner_in_matchday(matchday, supabase):
    """
    Return True if at least one user got all predictions correct for this matchday.
    Also saves winner(s) in the 'winners' table.
    """
    try:
        # --- Get predictions for this jornada ---
        predictions = (
            supabase.table("predictions")
            .select("username, home_team, away_team, prediction")
            .eq("jornada", matchday)
            .execute()
            .data or []
        )

        # --- Get actual results ---
        results = (
            supabase.table("results")
            .select("home_team, away_team, result")
            .eq("matchday", matchday)
            .execute()
            .data or []
        )

        if not predictions or not results:
            return False  # not enough data

        # --- Build result lookup map ---
        result_map = {
            (r["home_team"], r["away_team"]): r["result"]
            for r in results
            if r.get("result")
        }

        total_matches = len(result_map)
        if total_matches == 0:
            return False

        # --- Group predictions by user ---
        user_predictions = {}
        for p in predictions:
            user_predictions.setdefault(p["username"], []).append(p)

        winners = []

        # --- Check each user ---
        for user, preds in user_predictions.items():
            correct = 0
            for p in preds:
                key = (p["home_team"], p["away_team"])
                if key in result_map and p["prediction"] == result_map[key]:
                    correct += 1
            if correct == total_matches:
                print(f"✅ Winner found in jornada {matchday}: {user}")
                winners.append(user)

        # --- If there are winners, save them in DB ---
        if winners:
            for user in winners:
                supabase.table("winners").upsert(
                    {"username": user, "matchday": matchday}
                ).execute()
            return True

        return False

    except Exception as e:
        print(f"⚠️ Error in winner_in_matchday({matchday}): {e}")
        return False


def update_jackpot(supabase):
    """
    Compute jackpot evolution across all matchdays up to today.
    - Each jornada adds 16 units if no winner.
    - Resets to 16 when someone wins.
    """
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")

        # --- Get all past matchdays ---
        past_res = (
            supabase.table("matchdays")
            .select("number, date")
            .lt("date", today)
            .order("date", desc=False)
            .execute()
        )
        past_matchdays = past_res.data or []

        # --- Get the next (upcoming) matchday ---
        next_res = (
            supabase.table("matchdays")
            .select("number, date")
            .gte("date", today)
            .order("date", desc=False)
            .limit(1)
            .execute()
        )
        next_matchday = next_res.data or []

        # --- Combine both lists ---
        matchdays = past_matchdays + next_matchday

        if not matchdays:
            print("⚠️ No past jornadas found.")
            return

        acc = 0
        for i, jornada in enumerate(matchdays):
            num = jornada["number"]

            # For the first jornada, initialize
            if i == 0:
                acc = 0
                supabase.table("jackpot").upsert(
                    {"matchday": num, "accumulated": acc}
                ).execute()
                continue

            # For subsequent jornadas
            has_winner = winner_in_matchday(num, supabase)
            if has_winner:
                acc = 16
            else:
                acc += 16

            # Insert or update jackpot for this jornada
            supabase.table("jackpot").upsert(
                {"matchday": num, "accumulated": acc}
            ).execute()

        print("✅ Jackpot table updated successfully.")

    except Exception as e:
        print(f"⚠️ Error in update_jackpot: {e}")



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

    # It's already created so we do not need to update it

    #update_matchdays(data, supabase)

    #update_teams_table(data, supabase)

    update_results_table(data, supabase)

    update_classification_table(data, supabase)

    update_jackpot(supabase)
    
    update_last_refresh(supabase)