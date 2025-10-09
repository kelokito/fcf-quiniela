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
    df_class = df_class.rename(columns={
        "username": "User",
        "position": "Position",
        "points": "Points"
    })

    st.dataframe(
        df_class[["Position", "User", "Points"]],
        use_container_width=True,
        hide_index=True
    )
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
    st.info("No hit ratio data available yet.")

# ---------------- JACKPOT ----------------
st.subheader("💰 Current Jackpot")

bote = get_jackpot()
st.metric(label="Total Jackpot", value=f"{bote} €")

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("Data updates automatically from Supabase · Powered by Streamlit ⚡")
