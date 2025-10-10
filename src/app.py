import streamlit as st
from logic import get_prediction_distribution, get_number_of_users, get_matchday, save_predictions_db, get_matches, get_existing_users, get_match_predictions
import pandas as pd

st.set_page_config(page_title="Futsal Predictor", layout="centered")

# --- Cached functions ---
# Cache for functions that fetch data from your 'logic' module.
# Adjust ttl (time to live) based on how frequently your data updates.

@st.cache_data(ttl=3600) # Cache for 1 hour (matchday might change more often)
def cached_get_matchday():
    return get_matchday()

@st.cache_data(ttl=3600) # Cache for 1 hour
def cached_get_matches(jornada_number):
    return get_matches(jornada_number)

@st.cache_data(ttl=60) # Cache for 1 minute (distributions might update more frequently)
def cached_get_prediction_distribution(home_team, away_team):
    return get_prediction_distribution(home_team, away_team)

@st.cache_data(ttl=60) # Cache for 1 minute
def cached_get_match_predictions(home_team, away_team):
    return get_match_predictions(home_team, away_team)


# --- Title and description ---
st.title("⚽ Futsal Predictor - Senior B")
st.caption("Predict the next Jornada (1X2)")

# Initialize session state for predictions if not already present
# This will store the selected prediction for each match
if 'predictions_state' not in st.session_state:
    st.session_state.predictions_state = {}

# --- Get username ---
user_list = get_existing_users()
if not user_list:
    user_list = ["Select user", "User1", "User2", "User3"]  # fallback example

username = st.selectbox("Select your username:", user_list, index=None)
# Store selected username in session state for consistency if needed later
if username and username != "Select user":
    st.session_state.selected_username = username
else:
    st.session_state.selected_username = None


# --- Load match data ---
matchday = cached_get_matchday() # Use cached function
st.subheader(f"Jornada {matchday['number']} - {matchday['date']}")

# --- Custom CSS (mostly for layout, we'll use Streamlit's type for selection highlight) ---
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

/* Change the default primary button color to green */
.stButton>button[data-testid="stConnectionStatus"] { /* This targets primary buttons */
    background-color: #4CAF50 !important; /* Green */
    color: white !important;
    border-color: #4CAF50 !important;
}
.stButton>button:active {
    background-color: #4CAF50 !important; /* Green */
    border-color: #4CAF50 !important;
}

/* Style for selected buttons (primary type) */
.stButton>button[data-testid="base-button-secondary"]:not(:hover) { /* Secondary buttons not hovered */
    background-color: #f0f2f6; /* Default light grey for unselected */
    color: #333;
    border-color: #f0f2f6;
}

/* Responsive mobile */
@media (max-width:640px){
    div[data-testid="stColumn"]{min-width:50px;max-width:80px;}
}
.st-emotion-cache-1permvm{ justify-content:center}
</style>
""", unsafe_allow_html=True)

# --- Display matches ---
current_predictions_for_saving = {} # This dict will be used to collect predictions for saving
matches = cached_get_matches(matchday['number']) # Use cached function

for i, match in enumerate(matches):
    home_team = match["home_team"]
    away_team = match["away_team"]
    home_logo = match.get("home_logo")
    away_logo = match.get("away_logo")
    result = match.get("result") # Actual match result if available

    match_id_str = f"{home_team.replace(' ', '_')}-{away_team.replace(' ', '_')}" # Use sanitized ID for keys
    match_name = f"{home_team} vs {away_team}"
    prediction_state_key = f"pred_{match_id_str}" # Key for st.session_state

    # Ensure this match's prediction state exists
    if prediction_state_key not in st.session_state.predictions_state:
        # Here, if a username is selected, you might want to load existing predictions for this match.
        # This would require a new function in logic.py to fetch a single user's prediction for a match.
        # Example:
        # if st.session_state.selected_username and st.session_state.selected_username != "Select user":
        #     user_pred_for_match = get_user_match_prediction(st.session_state.selected_username, matchday['number'], home_team, away_team)
        #     st.session_state.predictions_state[prediction_state_key] = user_pred_for_match
        # else:
        st.session_state.predictions_state[prediction_state_key] = None # Default to no selection

    # Retrieve the current selection for this match
    current_selected_prediction = st.session_state.predictions_state.get(prediction_state_key)

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

    # --- Prediction selection buttons ---
    col1, col2, col3 = st.columns(3)
    disabled = result is not None  # disable buttons if match already played

    with col1:
        # Set button type to "primary" if this button's value ("1") matches the stored selection
        if st.button("1", key=f"{match_id_str}-1", disabled=disabled,
                     type="primary" if current_selected_prediction == "1" else "secondary"):
            st.session_state.predictions_state[prediction_state_key] = "1"
    with col2:
        # Set button type to "primary" if this button's value ("X") matches the stored selection
        if st.button("X", key=f"{match_id_str}-X", disabled=disabled,
                     type="primary" if current_selected_prediction == "X" else "secondary"):
            st.session_state.predictions_state[prediction_state_key] = "X"
    with col3:
        # Set button type to "primary" if this button's value ("2") matches the stored selection
        if st.button("2", key=f"{match_id_str}-2", disabled=disabled,
                     type="primary" if current_selected_prediction == "2" else "secondary"):
            st.session_state.predictions_state[prediction_state_key] = "2"

    # --- Stats display ---
    dist = cached_get_prediction_distribution(home_team, away_team) # Use cached function
    users_who_predicted_this_match = cached_get_match_predictions(home_team, away_team) # Use cached function

    st.markdown("<div style='margin-top:-10px;'></div>", unsafe_allow_html=True)
    col1_stats, col2_stats, col3_stats = st.columns(3) # Use different variable names to avoid conflict

    for col, opt in zip([col1_stats, col2_stats, col3_stats], ["1", "X", "2"]):
        with col:
            pct = round(dist.get(opt, 0) * 100, 1)
            # Filter users for this specific prediction option
            names = ", ".join(users_who_predicted_this_match.get(opt, []))
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

    # Store the prediction in the main dict for saving
    current_predictions_for_saving[match_id_str] = {
        "match": match_name,
        "home_team": home_team,
        "away_team": away_team,
        "prediction": current_selected_prediction or "", # Store the selected value
    }

    # Divider between matches (except last one)
    if i < len(matches) - 1:
        st.divider()

st.markdown("---")


# --- Save predictions ---
# Check if all matches have a prediction (not None or empty string)
all_predicted = all(
    (st.session_state.predictions_state.get(f"pred_{match_id_str}") is not None)
    for match_id_str in current_predictions_for_saving.keys()
)

if st.button("💾 Save Predictions"):
    # Use st.session_state.selected_username for consistency
    if not st.session_state.selected_username : # Check for default selection
        st.warning("Please select your username before saving.")
    elif not all_predicted:
        st.warning("⚠️ Please fill in predictions for ALL matches before saving.")
    else:
        # Prepare predictions in the format expected by save_predictions_db
        predictions_to_save = {
            match_id: {
                "match": details["match"],
                "home_team": details["home_team"],
                "away_team": details["away_team"],
                "prediction": details["prediction"]
            }
            for match_id, details in current_predictions_for_saving.items()
            if details["prediction"] # Ensure only non-empty predictions are saved
        }
        print("Predictions to save:", predictions_to_save) # For debugging
        save_predictions_db(st.session_state.selected_username, matchday['number'], predictions_to_save)
        st.success("✅ Predictions saved successfully!")

# --- Statistics ---
st.subheader("📊 Statistics")

# --- Number of users who answered ---
num_users = get_number_of_users(matchday['number']) # Use cached function
total_users = len(get_existing_users())
st.metric(
    label="Number of users who have answered",
    value=f"{num_users} / {total_users}"
)
# --- Current classification ---
#st.subheader("Current Classification")