import sqlite3, pandas as pd, streamlit as st, plotly.express as px

st.title("TESTING DEPLOYMENT - NEW VERSION v3")

@st.cache_data  # keeps queries fast for all users :contentReference[oaicite:1]{index=1}
def load_db(path="scores.db"):
    con = sqlite3.connect(path)
    df  = pd.read_sql("SELECT * FROM scores", con)  # table name
    con.close()
    return df

df = load_db()

# Define a color map for events globally
color_map = {
    "Vault": "blue",
    "Bars": "red",
    "Beam": "green",
    "Floor": "purple",
    "All Around": "orange"
}

# ----- SIDEBAR DRILL-DOWN ----------------------------------------------------
view = st.sidebar.radio("View", ["All athletes", "By team", "By athlete"])

if view == "By team":
    selected_level_team = st.sidebar.selectbox("Choose team (Level)", sorted(df.Level.unique()), key="team_level_selector")
    
    team_data_for_level = df[df.Level == selected_level_team]

    if team_data_for_level.empty:
        st.warning(f"No data available for Level {selected_level_team}.")
        st.stop()

    available_years = sorted(team_data_for_level.CompYear.unique(), reverse=True)
    if not available_years:
        st.warning(f"No competition year data available for Level {selected_level_team}.")
        st.stop()
    
    selected_year = st.sidebar.selectbox("Choose CompYear", available_years, key="team_year_selector")
    
    st.header(f"Team {selected_level_team} - Average Scores in {selected_year}")

    year_team_data_for_level = team_data_for_level[team_data_for_level.CompYear == selected_year]

    if year_team_data_for_level.empty:
        st.warning(f"No data available for Level {selected_level_team} in {selected_year}.")
        st.stop()

    events = ["Vault", "Bars", "Beam", "Floor", "All Around"]

    for event in events:
        event_data_for_team_year = year_team_data_for_level[year_team_data_for_level.Event == event]
        
        if not event_data_for_team_year.empty:
            # Calculate average score per meet, ensuring chronological order by MeetDate
            # MeetDate is crucial for correct chronological plotting if MeetNames are not unique or not in order
            # Assuming MeetDate column exists and is in a sortable format (e.g., YYYY-MM-DD or datetime)
            if 'MeetDate' not in event_data_for_team_year.columns:
                st.error("MeetDate column is missing, cannot guarantee chronological order for meets.")
                # Fallback to sorting by MeetName if MeetDate is not available
                avg_event_scores = event_data_for_team_year.groupby("MeetName", as_index=False).Score.mean()
            else:
                avg_event_scores = event_data_for_team_year.groupby(["MeetName", "MeetDate"], as_index=False).Score.mean()
                avg_event_scores = avg_event_scores.sort_values(by="MeetDate")

            if not avg_event_scores.empty:
                st.subheader(event)
                
                current_y_axis_range = None
                if event == "All Around":
                    current_y_axis_range = [30.0, 40.0] # Adjust if team AA averages differ significantly
                else:
                    current_y_axis_range = [5.5, 10.0]
            
                fig = px.line(avg_event_scores, x="MeetName", y="Score", 
                                markers=True, title=f"{event} - Average Team Scores",
                                color_discrete_sequence=[color_map.get(event, "black")],
                                text="Score")
                
                fig.update_layout(
                    height=600,
                    title_font_size=24,
                    xaxis_title_font_size=18,
                    yaxis_title_font_size=18,
                    legend_title_font_size=16, # Though no legend is shown for single color lines
                    legend_font_size=14
                )
                fig.update_traces(line=dict(width=4), marker=dict(size=10), textposition="top center", texttemplate='%{text:.3f}')

                if not avg_event_scores.empty:
                    max_score_row = avg_event_scores.loc[avg_event_scores['Score'].idxmax()]
                    fig.add_annotation(x=max_score_row['MeetName'], y=max_score_row['Score'],
                                       text="⭐", showarrow=False, font=dict(size=20))

                if current_y_axis_range:
                    fig.update_yaxes(range=current_y_axis_range)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.subheader(event)
                st.write(f"No average score data available for {event} for Level {selected_level_team} in {selected_year}.")
        else:
            st.subheader(event)
            st.write(f"No data available for {event} for Level {selected_level_team} in {selected_year}.")

elif view == "By athlete":
    athlete = st.sidebar.selectbox("Choose athlete", sorted(df.AthleteName.unique()))
    sub     = df[df.AthleteName == athlete]

    # Get unique levels for the athlete
    levels = sorted(sub.Level.unique())
    if not levels:
        st.warning(f"No data available for athlete {athlete}.")
        st.stop()

    selected_level = st.sidebar.selectbox("Choose Level", levels, index=0)
    
    show_current_year_only = st.sidebar.checkbox("Show most recent CompYear only", False)
    
    # Filter data by selected Level
    sub_level_data = sub[sub.Level == selected_level]

    if sub_level_data.empty:
        st.warning(f"No data available for {athlete} at Level {selected_level}.")
        st.stop()

    data_to_plot = sub_level_data.copy()
    
    if show_current_year_only:
        if not data_to_plot.empty:
            most_recent_comp_year = data_to_plot.CompYear.max()
            data_to_plot = data_to_plot[data_to_plot.CompYear == most_recent_comp_year]
            st.header(f"{athlete} - Level {selected_level} ({most_recent_comp_year})")
        else:
            st.header(f"{athlete} - Level {selected_level}") # Should not happen if sub_level_data was not empty
    else:
        st.header(f"{athlete} - Level {selected_level} (All Years)")
        # Ensure CompYear is string for categorical coloring, and sort for legend
        if 'CompYear' in data_to_plot.columns:
            data_to_plot['CompYear'] = data_to_plot['CompYear'].astype(str)

    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", False)
    y_axis_range = None

    # Events to plot
    events = ["Vault", "Bars", "Beam", "Floor", "All Around"]
    
    for event in events:
        event_data = data_to_plot[data_to_plot.Event == event]
        if not event_data.empty:
            st.subheader(event)
            # Sort by MeetDate to ensure chronological order, then by CompYear if MeetNames are not unique across years
            event_data = event_data.sort_values(by=["CompYear", "MeetDate"])
            
            current_y_axis_range = None
            if not fit_y_axis:
                if event == "All Around":
                    current_y_axis_range = [30.0, 40.0]
                else:
                    current_y_axis_range = [5.5, 10.0]
            
            plot_color_arg = "CompYear" if not show_current_year_only and len(event_data.CompYear.unique()) > 1 else None
            
            # Use the event-specific color from color_map if not coloring by CompYear
            discrete_color_sequence = [color_map.get(event, "black")] if plot_color_arg is None else None

            fig = px.line(event_data, x="MeetName", y="Score", 
                            color=plot_color_arg,
                            markers=True, title=event,
                            color_discrete_sequence=discrete_color_sequence,
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
            st.write(f"No data available for {event} at Level {selected_level}" + (f" in {most_recent_comp_year}." if show_current_year_only and 'most_recent_comp_year' in locals() else "."))

    # --- START: Multi-Year Comparison Logic ---
    # This logic is largely replaced or made redundant by the new Level-based multi-year line charts.
    # Commenting out for now.
    '''
    if not sub_year.empty: # Athlete has data for the selected_comp_year
        current_level_series = sub_year.Level.unique()
        
        if len(current_level_series) == 1: # Athlete competed at a single, unambiguous level in selected_comp_year
            current_level = current_level_series[0]

            # Get all data for this athlete at this specific level across all years
            all_data_at_current_level = sub[sub.Level == current_level]
            
            # Get all unique competition years the athlete competed at this level
            all_comp_years_at_this_level = sorted(all_data_at_current_level.CompYear.unique())

            if len(all_comp_years_at_this_level) > 1: # Only offer comparison if athlete competed at this level in multiple years
                
                # Meets attended by the athlete in the primary selected_comp_year at current_level
                meets_in_selected_year_at_level = sorted(sub_year[sub_year.Level == current_level].MeetName.unique())

                if meets_in_selected_year_at_level:
                    st.sidebar.markdown("---") # Visual separator in sidebar
                    st.sidebar.subheader(f"Multi-Year Meet Comparison (Level {current_level})")
                    
                    selected_comparison_meet = st.sidebar.selectbox(
                        f"Select Meet to Compare (Level {current_level})",
                        meets_in_selected_year_at_level,
                        index=0, # Default to the first meet
                        key=f"multi_year_comparison_meet_{athlete}_{selected_comp_year}_{current_level}" # Unique key
                    )

                    if selected_comparison_meet:
                        # Filter all data at current_level for the selected_comparison_meet
                        comparison_df = all_data_at_current_level[all_data_at_current_level.MeetName == selected_comparison_meet]
                        
                        # Ensure we are only comparing years where the athlete actually participated in this meet at this level
                        # This is mostly handled by the MeetName filter but good to be explicit with CompYear scope
                        comparison_df = comparison_df[comparison_df.CompYear.isin(all_comp_years_at_this_level)]

                        if not comparison_df.empty:
                            st.markdown("---") # Visual separator in main area
                            st.header(f"Score Comparison: {selected_comparison_meet} (Level {current_level})")
                            
                            # Sort CompYear for chronological display in legend and bars
                            # Ensure CompYear is string for Plotly categorical coloring, then sort numerically
                            comparison_df['CompYear'] = comparison_df['CompYear'].astype(str)
                            sorted_comp_years_for_chart = sorted(comparison_df.CompYear.unique(), key=lambda y_str: int(y_str))
                            
                            st.subheader(f"Comparing Years: {', '.join(sorted_comp_years_for_chart)}")
                            
                            events_order = ["Vault", "Bars", "Beam", "Floor", "All Around"]
                            comparison_df['Event'] = pd.Categorical(comparison_df['Event'], categories=events_order, ordered=True)
                            comparison_df = comparison_df.dropna(subset=['Event']) # Drop if event is not in our defined list
                            comparison_df = comparison_df.sort_values('Event')

                            # Apply All Around average: Score / 4
                            if 'All Around' in comparison_df['Event'].values:
                                aa_condition = comparison_df['Event'] == 'All Around'
                                comparison_df.loc[aa_condition, 'Score'] = comparison_df.loc[aa_condition, 'Score'] / 4
                            
                            fig_compare = px.bar(
                                comparison_df,
                                x="Event",
                                y="Score",
                                color="CompYear",
                                barmode="group",
                                title=f"Event Scores at {selected_comparison_meet} (Level {current_level})",
                                labels={"Score": "Score", "Event": "Event", "CompYear": "Competition Year"},
                                text="Score",
                                category_orders={"CompYear": sorted_comp_years_for_chart} # Chronological order
                            )
                            fig_compare.update_traces(texttemplate='%{text:.3f}', textposition='outside')
                            fig_compare.update_layout(
                                yaxis_title="Score",
                                yaxis_range=[5.5, 10.0], # User-defined fixed y-axis
                                legend_title_text="Year",
                                height=500 
                            )
                            st.plotly_chart(fig_compare, use_container_width=True)
                        else:
                            st.info(f"No detailed score data available to compare for {selected_comparison_meet} across relevant years at Level {current_level}.")
                else:
                    st.sidebar.info(f"No meets found for {athlete} in {selected_comp_year} at Level {current_level} to enable multi-year comparison.")
            else:
                st.sidebar.info(f"{athlete} has not competed at Level {current_level} in multiple years. Multi-year comparison not available.")
        elif len(current_level_series) == 0:
             st.sidebar.warning(f"No level information found for {athlete} in {selected_comp_year}.")
        else: # len(current_level_series) > 1
            st.sidebar.warning(f"{athlete} competed at multiple levels in {selected_comp_year}. Please refine data or select a year with a single level for comparison.")
    '''
    # --- END: Multi-Year Comparison Logic ---

else:  # All athletes
    pool = df.groupby(["CompYear", "Event"]).Score.mean().reset_index()
    st.header("Entire Pool – Average Scores")
    st.plotly_chart(px.line(pool, x="CompYear", y="Score",
                            color="Event", markers=True))
