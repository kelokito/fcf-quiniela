import streamlit as st
import json
import duckdb
from datetime import datetime
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "futbolcalendar"
DATA_FILE = DATA_DIR / "futsal_calendar.json"
DB_FILE = DATA_DIR / "predictions.duckdb"

st.set_page_config(page_title="Futsal Predictor", layout="centered")

# --- Helper functions ---
def load_data():
    if not DATA_FILE.exists():
        st.error("⚠️ No match data found. Please run the scraper first.")
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def init_db():
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
    con = init_db()
    timestamp = datetime.now()
    for match, pred in predictions.items():
        con.execute(
            "INSERT INTO predictions VALUES (?, ?, ?, ?, ?)",
            [username, jornada, timestamp, match, pred]
        )
    con.close()

def get_next_jornada(data):
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


# --- UI ---
st.title("⚽ Futsal Predictor")
st.caption("Predict the next Jornada (1X2)")

username = st.text_input("Enter your username:")

data = load_data()
if not data:
    st.stop()

next_jornada = get_next_jornada(data)
st.subheader(f"{next_jornada['jornada']} — {next_jornada['date']}")

predictions = {}

# --- Custom CSS for styling ---
st.markdown("""
    <style>
    .match-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 18px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        background-color: white;
    }
    .teams-line {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
        font-size: 16px;
        text-align: center;
        margin-bottom: 8px;
    }
    .prediction-buttons {
        display: flex;
        justify-content: center;
        gap: 10px;
    }
    .prediction-buttons button {
        flex: 1;
        padding: 8px 0;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        background-color: #f0f0f0;
        transition: background-color 0.2s;
    }
    .prediction-buttons button.selected-1 { background-color: #a8e6cf; }
    .prediction-buttons button.selected-X { background-color: #ffd3b6; }
    .prediction-buttons button.selected-2 { background-color: #ff8b94; }
    </style>
""", unsafe_allow_html=True)

# --- Match cards ---
for match in next_jornada["matches"]:
    match_name = f"{match['home_team']} vs {match['away_team']}"

    st.markdown("<div class='match-card'>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class='teams-line'>
            <div><img src="{match['home_logo']}" width="30"> {match['home_team']}</div>
            <div>vs</div>
            <div>{match['away_team']} <img src="{match['away_logo']}" width="30"></div>
        </div>
    """, unsafe_allow_html=True)

    # Button-based prediction form
    cols = st.columns(3)
    for i, opt in enumerate(["1", "X", "2"]):
        with cols[i]:
            if st.button(opt, key=f"{match_name}-{opt}"):
                st.session_state[f"pred_{match_name}"] = opt

    selected = st.session_state.get(f"pred_{match_name}", None)
    if selected:
        st.markdown(
            f"<div style='text-align:center;font-size:14px;color:gray;'>Selected: <b>{selected}</b></div>",
            unsafe_allow_html=True
        )
    st.markdown("</div>", unsafe_allow_html=True)
    predictions[match_name] = selected or ""

st.markdown("---")

# --- Save button ---
if st.button("💾 Save Predictions"):
    if not username.strip():
        st.warning("Please enter your username before saving.")
    else:
        # Only save if at least one prediction made
        valid_preds = {m: p for m, p in predictions.items() if p}
        if not valid_preds:
            st.warning("Please make at least one prediction before saving.")
        else:
            save_predictions_db(username, next_jornada["jornada"], valid_preds)
            st.success("✅ Predictions saved successfully!")

# --- View previous predictions ---
with st.expander("📊 View all predictions"):
    con = init_db()
    df = con.execute("SELECT * FROM predictions ORDER BY timestamp DESC").df()
    con.close()
    st.dataframe(df)
