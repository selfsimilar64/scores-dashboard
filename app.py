import sqlite3, pandas as pd, streamlit as st, plotly.express as px

st.title("TESTING DEPLOYMENT - NEW VERSION v2")

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
    y_axis_range = None # Default to None (fit to data)

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
            
            current_y_axis_range = None
            if not fit_y_axis:
                if event == "All Around":
                    current_y_axis_range = [30.0, 40.0]
                else:
                    current_y_axis_range = [5.5, 10.0]
            
            fig = px.line(event_data, x="MeetName", y="Score", markers=True, title=event,
                            color_discrete_sequence=[color_map.get(event, "black")],
                            text="Score") # Add text for data labels
            fig.update_layout(
                height=600,
                title_font_size=24,      # Increase title font size
                xaxis_title_font_size=18, # Increase x-axis label font size
                yaxis_title_font_size=18, # Increase y-axis label font size
                legend_title_font_size=16, # Increase legend title font size
                legend_font_size=14       # Increase legend font size
            )
            fig.update_traces(line=dict(width=4), marker=dict(size=10), textposition="top center") # Position data labels

            # Highlight highest score
            if not event_data.empty:
                max_score_row = event_data.loc[event_data['Score'].idxmax()]
                fig.add_annotation(x=max_score_row['MeetName'], y=max_score_row['Score'],
                                   text="⭐", showarrow=False, font=dict(size=20))

            if current_y_axis_range: # Apply the determined y-axis range
                fig.update_yaxes(range=current_y_axis_range)
            st.plotly_chart(fig, use_container_width=True) # Make graph use full width
        else:
            st.subheader(event)
            st.write(f"No data available for {event} in {selected_comp_year}.")

    # --- START: New Year-over-Year Comparison Logic ---
    if not sub.empty and comp_years: # 'sub' is athlete's data, 'comp_years' is their sorted list of comp years
        previous_comp_year_value = None
        if selected_comp_year in comp_years:
            current_year_index = comp_years.index(selected_comp_year)
            # comp_years is sorted reverse=True, so next index is previous year
            if current_year_index + 1 < len(comp_years):
                previous_comp_year_value = comp_years[current_year_index + 1]

        if previous_comp_year_value is not None:
            # Data for the selected comp_year is already in sub_year
            # sub_year = sub[sub.CompYear == selected_comp_year]

            # Data for the previous comp_year for this athlete
            previous_year_athlete_data = sub[sub.CompYear == previous_comp_year_value]

            if not previous_year_athlete_data.empty and not sub_year.empty:
                current_level_series = sub_year.Level.unique()
                previous_level_series = previous_year_athlete_data.Level.unique()

                # Ensure athlete competed at a single, consistent level within each of these years
                if len(current_level_series) == 1 and len(previous_level_series) == 1:
                    current_level = current_level_series[0]
                    previous_level = previous_level_series[0]

                    if current_level == previous_level:
                        # Find common meets
                        current_year_meets = sub_year.MeetName.unique()
                        previous_year_meets = previous_year_athlete_data.MeetName.unique()
                        
                        common_meets = sorted(list(set(current_year_meets) & set(previous_year_meets)))

                        if common_meets:
                            st.sidebar.markdown("---") # Visual separator in sidebar
                            st.sidebar.subheader("Year-over-Year Comparison")
                            
                            comp_year_display = str(selected_comp_year)
                            prev_comp_year_display = str(previous_comp_year_value)

                            selected_comparison_meet = st.sidebar.selectbox(
                                f"Compare Meet: {comp_year_display} vs {prev_comp_year_display} (Lvl {current_level})",
                                common_meets,
                                index=0, # Default to the first common meet
                                key=f"comparison_meet_{athlete}_{selected_comp_year}" # Unique key
                            )

                            if selected_comparison_meet:
                                current_meet_scores_for_compare = sub_year[sub_year.MeetName == selected_comparison_meet]
                                previous_meet_scores_for_compare = previous_year_athlete_data[previous_year_athlete_data.MeetName == selected_comparison_meet]
                                
                                comparison_df = pd.concat([
                                    current_meet_scores_for_compare, 
                                    previous_meet_scores_for_compare
                                ])

                                if not comparison_df.empty:
                                    st.markdown("---") # Visual separator in main area
                                    st.header(f"Score Comparison at {selected_comparison_meet}")
                                    st.subheader(f"Level {current_level}: {comp_year_display} vs. {prev_comp_year_display}")
                                    
                                    events_order = ["Vault", "Bars", "Beam", "Floor", "All Around"]
                                    comparison_df['Event'] = pd.Categorical(comparison_df['Event'], categories=events_order, ordered=True)
                                    comparison_df = comparison_df.dropna(subset=['Event'])
                                    comparison_df = comparison_df.sort_values('Event')

                                    # Ensure CompYear is treated as categorical for distinct colors and legend
                                    comparison_df['CompYear'] = comparison_df['CompYear'].astype(str)

                                    # --- START: Modify All Around score to be an average ---
                                    if 'All Around' in comparison_df['Event'].values:
                                        aa_condition = comparison_df['Event'] == 'All Around'
                                        comparison_df.loc[aa_condition, 'Score'] = comparison_df.loc[aa_condition, 'Score'] / 4
                                    # --- END: Modify All Around score to be an average ---
                                    
                                    fig_compare = px.bar(
                                        comparison_df,
                                        x="Event",
                                        y="Score",
                                        color="CompYear",
                                        barmode="group",
                                        title=f"Event Scores: {comp_year_display} vs {prev_comp_year_display}",
                                        labels={"Score": "Score", "Event": "Event", "CompYear": "Competition Year"},
                                        text="Score",
                                        category_orders={"CompYear": sorted([comp_year_display, prev_comp_year_display], reverse=True)}
                                    )
                                    fig_compare.update_traces(texttemplate='%{text:.3f}', textposition='outside')
                                    fig_compare.update_layout(
                                        yaxis_title="Score",
                                        yaxis_range=[5.5, 10.0],
                                        legend_title_text="Year",
                                        height=500 
                                    )
                                    st.plotly_chart(fig_compare, use_container_width=True)
                                else:
                                    st.info(f"No detailed score data available to compare for {selected_comparison_meet} between these years.")
                        else: 
                            st.sidebar.info(f"No common meets for {comp_year_display} & {prev_comp_year_display} at Level {current_level}.")
    # --- END: New Year-over-Year Comparison Logic ---

else:  # All athletes
    pool = df.groupby(["CompYear", "Event"]).Score.mean().reset_index()
    st.header("Entire Pool – Average Scores")
    st.plotly_chart(px.line(pool, x="CompYear", y="Score",
                            color="Event", markers=True))
