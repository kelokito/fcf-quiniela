import streamlit as st
import pandas as pd
from logic import get_top_users, get_classification, get_users_hits_last_matchday, get_jackpot

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="📊 Statistics", layout="wide")

st.title("📊 Competition Statistics")
st.markdown("Explore the latest stats, rankings, and hit ratios from the prediction game.")

# ---------------- CLASSIFICATION TABLE ----------------
st.subheader("🏆 Classification Table")

classification = get_classification()
if classification:
    df_class = pd.DataFrame(classification)

    # Prepare data for display
    df_class["Avg. Home Pts"] = df_class["home_points_ratio"].apply(lambda x: f"{x:.2f}")
    df_class["Avg. Away Pts"] = df_class["away_points_ratio"].apply(lambda x: f"{x:.2f}")
    df_class["Avg. GF"] = df_class["avg_goals_favor"].apply(lambda x: f"{x:.2f}")
    df_class["Avg. GA"] = df_class["avg_goals_against"].apply(lambda x: f"{x:.2f}")

    # Create the 'Team' column with image and name
    df_class["Team"] = df_class.apply(
        lambda row: f"<img src='{row['logo']}' width='30' style='vertical-align:middle; margin-right:5px;'></img> {row['name']}"
        if pd.notna(row['logo']) and row['logo'] else row['name'], axis=1
    )

    # Rename other columns for display
    df_class = df_class.rename(columns={
        "position": "Pos.",
        "games_played": "Games Pld",
    })

    # Define the columns to display and their order
    display_columns = [
        "Pos.", "Team", "Games Pld",
        "Avg. Home Pts", "Avg. Away Pts", "Avg. GF", "Avg. GA"
    ]

    # Convert the DataFrame to HTML and render it with st.markdown
    # We use .to_html() and set escape=False to allow HTML tags in the 'Team' column
    html_table = df_class[display_columns].to_html(escape=False, index=False)
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown("---") # Separator

else:
    st.info("No classification data available yet.")

# ---------------- TOP USERS ----------------
st.subheader("🔥 Top Users (Most Correct Predictions)")

top_users = get_top_users()
if top_users:
    df_top = pd.DataFrame(top_users)
    df_top = df_top.rename(columns={"username": "User", "hits": "Hits"})

    st.bar_chart(df_top.set_index("User")["Hits"])
else:
    st.info("No prediction data available yet.")

# ---------------- LAST MATCHDAY PERFORMANCE ----------------
st.subheader("🎯 Last Matchday Hit Ratios")

ratios = get_users_hits_last_matchday()
if ratios:
    df_ratios = pd.DataFrame(ratios)
    df_ratios = df_ratios.rename(columns={"username": "User", "hit_ratio": "Hit Ratio"})
    df_ratios["Hit Ratio (%)"] = df_ratios["Hit Ratio"] * 100

    st.bar_chart(df_ratios.set_index("User")["Hit Ratio (%)"])
else:
    st.info("No hit ratio data available yet for the last matchday.")

# ---------------- JACKPOT ----------------
st.subheader("💰 Current Jackpot")

jackpot_value = get_jackpot()
st.metric(label="Total Jackpot", value=f"{jackpot_value} €")

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Data updates automatically from Supabase · Powered by Streamlit ⚡")