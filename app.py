import sqlite3, pandas as pd, streamlit as st, plotly.express as px

@st.cache_data  # keeps queries fast for all users :contentReference[oaicite:1]{index=1}
def load_db(path="scores.sqlite"):
    con = sqlite3.connect(path)
    df  = pd.read_sql("SELECT * FROM scores", con)  # table name
    con.close()
    return df

df = load_db()

# ----- SIDEBAR DRILL-DOWN ----------------------------------------------------
view = st.sidebar.radio("View", ["All athletes", "By team", "By athlete"])

if view == "By team":
    team = st.sidebar.selectbox("Choose team (Level)", sorted(df.Level.unique()))
    sub  = df[df.Level == team]
    st.header(f"Team {team}")
    st.plotly_chart(
        px.line(sub, x="CompYear", y="Score",
                color="Event", markers=True,
                title="Average event score by meet")
        .update_traces(opacity=0.6)
    )

elif view == "By athlete":
    athlete = st.sidebar.selectbox("Choose athlete", sorted(df.AthleteName.unique()))
    sub     = df[df.AthleteName == athlete]
    st.header(athlete)
    st.plotly_chart(px.line(sub, x="CompYear", y="Score",
                            color="Event", markers=True))

else:  # All athletes
    pool = df.groupby(["CompYear", "Event"]).Score.mean().reset_index()
    st.header("Entire Pool – Average Scores")
    st.plotly_chart(px.line(pool, x="CompYear", y="Score",
                            color="Event", markers=True))
