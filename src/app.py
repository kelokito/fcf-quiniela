import streamlit as st
from logic import get_all_predictions, get_prediction_distribution, get_number_of_users, get_next_jornada, save_predictions_db, load_data, get_existing_users, get_match_predictions
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

    # --- Prediction selection ---
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

    # --- Stats display ---
    dist = get_prediction_distribution(match["home_team"], match["away_team"])
    users = get_match_predictions(match["home_team"], match["away_team"])

    # --- Display distribution percentages and users under each button ---
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
        "home_team": match["home_team"],
        "away_team": match["away_team"],
        "prediction": selected or "",
    }

    if match != next_jornada["matches"][-1]:
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
    total_users = len(get_existing_users())
    st.metric(
        label="Number of users who have answered",
        value=f"{num_users} / {total_users}"
    )
    # --- Current classification ---
    st.subheader("Current Classification")
    # Example placeholder: replace with your real classification logic if available
    if 'classification' in df.columns and 'team' in df.columns:
        classification = df[['team','classification']].drop_duplicates().sort_values('classification', ascending=False)
        st.table(classification)
    else:
        st.info("Classification data not available yet.")