import sqlite3, pandas as pd, streamlit as st, plotly.express as px

st.title("TESTING DEPLOYMENT - NEW VERSION")

@st.cache_data  # keeps queries fast for all users :contentReference[oaicite:1]{index=1}
def load_db(path="scores.db"):
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
    
    # Add CompYear dropdown
    comp_years = sorted(sub.CompYear.unique(), reverse=True)
    selected_comp_year = st.sidebar.selectbox("Choose CompYear", comp_years, index=0)
    
    # Filter data by selected CompYear
    sub_year = sub[sub.CompYear == selected_comp_year]
    
    st.header(athlete)
    
    # Y-axis toggle
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", False)
    y_axis_range = None if fit_y_axis else [4.0, 10.0]

    # Events to plot
    events = ["Vault", "Bars", "Beam", "Floor", "All Around"]
    # Define a color map for events
    color_map = {
        "Vault": "blue",
        "Bars": "red",
        "Beam": "green",
        "Floor": "purple",
        "All Around": "orange"
    }

    for event in events:
        event_data = sub_year[sub_year.Event == event]
        if not event_data.empty:
            st.subheader(event)
            # Sort by MeetDate to ensure chronological order
            event_data = event_data.sort_values(by="MeetDate")
            fig = px.line(event_data, x="MeetName", y="Score", markers=True, title=event,
                            color_discrete_sequence=[color_map.get(event, "black")],
                            text="Score") # Add text for data labels
            fig.update_layout(height=600) # Increase graph height
            fig.update_traces(line=dict(width=4), marker=dict(size=10), textposition="top center") # Position data labels

            # Highlight highest score
            if not event_data.empty:
                max_score_row = event_data.loc[event_data['Score'].idxmax()]
                fig.add_annotation(x=max_score_row['MeetName'], y=max_score_row['Score'],
                                   text="⭐", showarrow=False, font=dict(size=20))

            if y_axis_range:
                fig.update_yaxes(range=y_axis_range)
            st.plotly_chart(fig, use_container_width=True) # Make graph use full width
        else:
            st.subheader(event)
            st.write(f"No data available for {event} in {selected_comp_year}.")

else:  # All athletes
    pool = df.groupby(["CompYear", "Event"]).Score.mean().reset_index()
    st.header("Entire Pool – Average Scores")
    st.plotly_chart(px.line(pool, x="CompYear", y="Score",
                            color="Event", markers=True))
