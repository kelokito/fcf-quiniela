import streamlit as st
from logic import get_prediction_distribution, get_number_of_users, get_matchday, save_predictions_db, get_matches, get_existing_users, get_match_predictions
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
matchday = get_matchday()
print(matchday)
st.subheader(f"Jornada {matchday['number']} - {matchday['date']}")

predictions = {}

# --- Custom CSS ---
st.markdown("""
<style>
.match-card {
    border:1px solid #ddd;border-radius:10px;padding:12px;margin-bottom:18px;
    box-shadow:0 2px 6px rgba(0,0,0,0.08);background-color:white;
}
.teams-line {
    display:flex;justify-content:space-between;align-items:center;
    font-weight:600;font-size:16px;text-align:center;margin-bottom:8px;
}
div[data-testid="stColumns"] {
    display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-bottom:8px;
}
div[data-testid="stColumn"] {
    flex-grow:1;flex-shrink:1;flex-basis:0;min-width:60px;max-width:200px;
    display:flex;justify-content:center;align-items:center;padding:0 5px;
}
.stButton>button {
    width:100%;padding:10px 20px;font-size:16px;border-radius:6px;
    cursor:pointer;margin:0;white-space:nowrap;transition:all 0.2s ease;
}

/* --- Selected styles --- */
.selected-light {
    background-color: #333 !important;
    color: #fff !important;
    opacity: 1 !important;  /* fully visible */
    border: 1px solid #fff !important;
}

.selected-dark {
    background-color: #eee !important;
    color: #000 !important;
    opacity: 1 !important;
    border: 1px solid #000 !important;
}

/* Responsive mobile */
@media (max-width:640px){
    div[data-testid="stColumn"]{min-width:50px;max-width:80px;}
}
.st-emotion-cache-1permvm{ justify-content:center}
</style>
""", unsafe_allow_html=True)

# --- Display matches ---
predictions = {}
matches = get_matches(matchday['number'])

# Assuming matches = get_matches(current_matchday)
# and next_jornada is available if needed

predictions = {}

for i, match in enumerate(matches):
    home_team = match["home_team"]
    away_team = match["away_team"]
    home_logo = match.get("home_logo")
    away_logo = match.get("away_logo")
    result = match.get("result")

    match_id = f"{home_team}-{away_team}"
    match_name = f"{home_team} vs {away_team}"

    # --- Display match info ---
    st.markdown(f"""
        <div class='teams-line' style='display:flex;justify-content:space-between;align-items:center;margin:8px 0;'>
            <div style='display:flex;align-items:center;gap:6px;'>
                <img src="{home_logo}" width="30"> <b>{home_team}</b>
            </div>
            <div>vs</div>
            <div style='display:flex;align-items:center;gap:6px;'>
                <b>{away_team}</b> <img src="{away_logo}" width="30">
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- Prediction selection ---
    col1, col2, col3 = st.columns(3)
    prediction_key = f"pred_{match_id}"
    disabled = result is not None  # disable buttons if match already played

    with col1:
        if st.button("1", key=f"{match_id}-1", disabled=disabled):
            st.session_state[prediction_key] = "1"
    with col2:
        if st.button("X", key=f"{match_id}-X", disabled=disabled):
            st.session_state[prediction_key] = "X"
    with col3:
        if st.button("2", key=f"{match_id}-2", disabled=disabled):
            st.session_state[prediction_key] = "2"

    selected = st.session_state.get(prediction_key, None)

    # --- Stats display ---
    dist = get_prediction_distribution(home_team, away_team)
    users = get_match_predictions(home_team, away_team)

    st.markdown("<div style='margin-top:-10px;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    for col, opt in zip([col1, col2, col3], ["1", "X", "2"]):
        with col:
            pct = round(dist.get(opt, 0) * 100, 1)
            names = ", ".join(users.get(opt, []))
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    font-size:14px;
                    margin-top:4px;
                    background-color:rgba(0,0,0,0.03);
                    border-radius:6px;
                    padding:6px;">
                    <b>{pct}%</b><br>
                    <span style='font-size:12px;color:gray;'>{names or '-'}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    if selected:
        st.markdown(
            f"<div style='text-align:center;font-size:14px;color:gray;'>Selected: <b>{selected}</b></div>",
            unsafe_allow_html=True
        )

    predictions[match_id] = {
        "match": match_name,
        "home_team": home_team,
        "away_team": away_team,
        "prediction": selected or "",
    }

    # Divider between matches (except last one)
    if i < len(matches) - 1:
        st.divider()

st.markdown("---")


# --- Save predictions ---
all_predicted = all(
    (p.get("prediction") if isinstance(p, dict) else p)
    for p in predictions.values()
)

if st.button("💾 Save Predictions"):
    if not username or not str(username).strip():
        st.warning("Please enter your username before saving.")
    elif not all_predicted:
        st.warning("⚠️ Please fill in predictions for ALL matches before saving.")
    else:
        print("Llego")
        valid_preds = {m: p for m, p in predictions.items() if p}
        save_predictions_db(username, matchday['number'], valid_preds)
        st.success("✅ Predictions saved successfully!")

# --- Statistics ---
st.subheader("📊 Statistics")

# --- Number of users who answered ---
num_users = get_number_of_users(matchday['number'])
st.metric("Number of users who have answered", num_users)

# --- Current classification ---
#st.subheader("Current Classification")
