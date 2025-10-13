# results.py
import streamlit as st
from logic import get_last_matchday, get_users_hits_last_matchday, get_matches, get_match_predictions, update_results, get_jackpot_for_matchday
import pandas as pd


with st.expander("🔄 Manual data refresh"):
    if st.button("Update results now"):
        res = update_results()
        if "success" in res:
            st.success(res["success"])
        else:
            st.warning(res.get("error", "⚠️ Unknown error occurred."))


st.set_page_config(page_title="📊 Futsal Results", layout="centered")

# --- Title ---
st.title("📋 Jornada Results - Futsal Predictor")

# --- Get current or last jornada ---
matchday = get_last_matchday()
if not matchday:
    st.warning("⚠️ No jornada data found.")
    st.stop()

st.subheader(f"Jornada {matchday['number']} - {matchday['date']}")

# --- Load matches ---
matches = get_matches(matchday["number"])
if not matches:
    st.info("No matches available for this jornada.")
    st.stop()

# --- Custom CSS ---
st.markdown("""
<style>
.match-card {
    border:1px solid #ddd;
    border-radius:10px;
    padding:12px;
    margin-bottom:18px;
    box-shadow:0 2px 6px rgba(0,0,0,0.08);
    background-color:white;
}
.teams-line {
    display:flex;
    justify-content:space-between;
    align-items:center;
    font-weight:600;
    font-size:16px;
    text-align:center;
    margin-bottom:8px;
}
.prediction-tag {
    display:inline-block;
    padding:4px 8px;
    border-radius:6px;
    font-weight:500;
    color:white;
    margin:2px;
}
.prediction-correct { background-color:#4CAF50; }  /* Green */
.prediction-wrong { background-color:#E74C3C; }    /* Red */
.prediction-pending { background-color:#BDC3C7; color:black; } /* Gray */
</style>
""", unsafe_allow_html=True)

# ---------------- JACKPOT ----------------
st.subheader("💰 Current Jackpot")

jackpot_value = get_jackpot_for_matchday(matchday["number"])
st.metric(label=f"Total Jackpot for Jornada {matchday['number']}", value=f"{jackpot_value} €")


# ---------------- LAST MATCHDAY PERFORMANCE ----------------
st.subheader("🎯 Matchday Hit Ratios")

ratios = get_users_hits_last_matchday()
if ratios:
    df_ratios = pd.DataFrame(ratios)
    df_ratios = df_ratios.rename(columns={"username": "User", "hit_ratio": "Hit Ratio"})
    df_ratios["Hit Ratio (%)"] = df_ratios["Hit Ratio"] * 100

    st.bar_chart(df_ratios.set_index("User")["Hit Ratio (%)"])
else:
    st.info("No hit ratio data available yet for the last matchday.")


# --- Display each match with results and predictions ---
for match in matches:
    home_team = match["home_team"]
    away_team = match["away_team"]
    home_logo = match.get("home_logo")
    away_logo = match.get("away_logo")
    result = match.get("result")

    # --- Header ---
    st.markdown(f"""
    <div class='match-card'>
        <div class='teams-line'>
            <div style='display:flex;align-items:center;gap:6px;'>
                <img src="{home_logo}" width="30"> <b>{home_team}</b>
            </div>
            <div>vs</div>
            <div style='display:flex;align-items:center;gap:6px;'>
                <b>{away_team}</b> <img src="{away_logo}" width="30">
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- Result display ---
    if result:
        st.markdown(f"<p style='text-align:center;font-size:18px;color:#4CAF50;'>Final Result: <b>{result}</b></p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align:center;font-size:16px;color:gray;'>Match not played yet</p>", unsafe_allow_html=True)

    # --- Get predictions for this match ---
    predictions = get_match_predictions(home_team, away_team)
    if not predictions:
        st.markdown("<p style='text-align:center;color:gray;'>No predictions yet.</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align:center;font-size:16px;margin-bottom:8px;'><b>User Predictions</b></p>", unsafe_allow_html=True)
        # Display predictions by outcome
        for outcome, users in predictions.items():
            if not users:
                continue
            color_class = (
                "prediction-correct" if result == outcome
                else "prediction-wrong" if result and result != outcome
                else "prediction-pending"
            )
            user_tags = " ".join([f"<span class='prediction-tag {color_class}'>{u}</span>" for u in users])
            st.markdown(
                f"<div style='text-align:center;margin-bottom:8px;'><b>{outcome}</b>: {user_tags}</div>",
                unsafe_allow_html=True
            )

    st.markdown("</div>", unsafe_allow_html=True)  # close match-card

st.success("✅ Results and predictions loaded successfully!")
