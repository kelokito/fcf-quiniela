import streamlit as st
from logic import init_db

st.set_page_config(page_title="Futsal Statistics", layout="centered")

st.title("📊 Futsal Statistics")
st.caption("View historical predictions and performance")

# --- Load data from database ---
con = init_db()
try:
    df = con.execute("SELECT * FROM predictions ORDER BY timestamp DESC").df()
finally:
    con.close()

if df.empty:
    st.warning("No predictions found yet.")
else:
    # Show raw data
    st.subheader("All Predictions")
    st.dataframe(df)

    # --- Example: Count of predictions per result ---
    st.subheader("Prediction Distribution")
    distribution = df[['prediction']].value_counts().reset_index()
    distribution.columns = ['Prediction', 'Count']
    st.bar_chart(distribution.set_index('Prediction'))

    # --- Example: Most active users ---
    st.subheader("Most Active Users")
    top_users = df['username'].value_counts().head(10)
    st.table(top_users)
