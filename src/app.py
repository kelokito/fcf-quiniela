import streamlit as st
from logic import get_all_predictions, get_prediction_distribution, get_number_of_users, get_next_jornada, save_predictions_db, load_data, get_existing_users
import pandas as pd

st.set_page_config(page_title="Futsal Predictor", layout="centered")

# --- Title and description ---
st.title("⚽ Futsal Predictor - Senior B")
st.caption("Predict the next Jornada (1X2)")

# --- Get username ---
user_list = get_existing_users()
if not user_list:
    user_list = ["Select user", "User1", "User2", "User3"]  # fallback example

username = st.selectbox("Select your username:", user_list, index=None)
# --- Load match data ---
data = load_data()
if not data:
    st.warning("No data loaded. Please check your data source.")
    st.stop()

next_jornada = get_next_jornada(data)
st.subheader(f"{next_jornada['jornada']} — {next_jornada['date']}")

predictions = {}

# --- Custom CSS ---
st.markdown("""
<style>
.match-card {border:1px solid #ddd;border-radius:10px;padding:12px;margin-bottom:18px;box-shadow:0 2px 6px rgba(0,0,0,0.08);background-color:white;}
.teams-line {display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:16px;text-align:center;margin-bottom:8px;}
div[data-testid="stColumns"] {display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:8px;}
div[data-testid="stColumn"] {flex-grow:1;flex-shrink:1;flex-basis:0;min-width:60px;max-width:200px;display:flex;justify-content:center;align-items:center;padding:0 5px;}
.stButton>button {width:100%;padding:10px 20px;font-size:16px;border-radius:6px;cursor:pointer;margin:0;white-space:nowrap;}
@media (max-width: 640px){div[data-testid="stColumn"]{min-width:50px;max-width:80px;}}
.st-emotion-cache-1permvm{ justify-content:center}
</style>
""", unsafe_allow_html=True)

# --- Display matches ---
for match in next_jornada["matches"]:
    match_id = match.get("id", f"{match['home_team']}-{match['away_team']}")
    match_name = f"{match['home_team']} vs {match['away_team']}"

    st.markdown(f"""
        <div class='teams-line'>
            <div><img src="{match['home_logo']}" width="30"> {match['home_team']}</div>
            <div>vs</div>
            <div>{match['away_team']} <img src="{match['away_logo']}" width="30"></div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    prediction_key = f"pred_{match_id}"

    with col1:
        if st.button("1", key=f"{match_id}-1"):
            st.session_state[prediction_key] = "1"
    with col2:
        if st.button("X", key=f"{match_id}-X"):
            st.session_state[prediction_key] = "X"
    with col3:
        if st.button("2", key=f"{match_id}-2"):
            st.session_state[prediction_key] = "2"

    selected = st.session_state.get(prediction_key, None)
    if selected:
        st.markdown(f"<div style='text-align:center;font-size:14px;color:gray;'>Selected: <b>{selected}</b></div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    predictions[match_name] = selected or ""

    if match != next_jornada["matches"][-1]:
        st.divider()

st.markdown("---")

# --- Save predictions ---
all_predicted = all(predictions.get(f"{match['home_team']} vs {match['away_team']}") 
                    for match in next_jornada["matches"])

if st.button("💾 Save Predictions"):
    if not username.strip():
        st.warning("Please enter your username before saving.")
    elif not all_predicted:
        st.warning("⚠️ Please fill in predictions for ALL matches before saving.")
    else:
        valid_preds = {m: p for m, p in predictions.items() if p}
        save_predictions_db(username, next_jornada["jornada"], valid_preds)
        st.success("✅ Predictions saved successfully!")

# --- Statistics ---
st.subheader("📊 Statistics")

df = get_all_predictions()

if df.empty:
    st.info("No predictions yet.")
else:
    # --- Number of users who answered ---
    num_users = get_number_of_users()
    st.metric("Number of users who have answered", num_users)

    # --- Prediction distribution per match ---
    st.subheader("Prediction Distribution per Match")
    for match in next_jornada["matches"]:
        match_name = f"{match['home_team']} vs {match['away_team']}"
        dist = get_prediction_distribution(match_name)  # Returns a dict like {'1': 0.4, 'X': 0.35, '2': 0.25}
        
        # Ensure order 1, X, 2
        dist_ordered = {k: dist.get(k, 0) for k in ["1", "X", "2"]}
        
        st.markdown(f"**{match_name}**")
        
        # Display percentages horizontally
        cols = st.columns(3)
        for i, opt in enumerate(["1", "X", "2"]):
            with cols[i]:
                st.markdown(f"<div style='text-align:center'>{opt}: {dist_ordered[opt]*100:.1f}%</div>", unsafe_allow_html=True)
        
        st.markdown("---")



    # --- Current classification ---
    st.subheader("Current Classification")
    # Example placeholder: replace with your real classification logic if available
    if 'classification' in df.columns and 'team' in df.columns:
        classification = df[['team','classification']].drop_duplicates().sort_values('classification', ascending=False)
        st.table(classification)
    else:
        st.info("Classification data not available yet.")