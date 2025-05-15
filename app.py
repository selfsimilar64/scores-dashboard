import sqlite3, pandas as pd, streamlit as st, plotly.express as px

st.title("TESTING DEPLOYMENT - NEW VERSION v4")

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

    # Get unique levels for the athlete, sorted by recency of CompYear
    if not sub.empty:
        athlete_levels_years = sub.groupby('Level')['CompYear'].max().reset_index()
        # Ensure CompYear is numeric before sorting, in case it's read as string
        athlete_levels_years['CompYear'] = pd.to_numeric(athlete_levels_years['CompYear'], errors='coerce')
        athlete_levels_years = athlete_levels_years.sort_values(by='CompYear', ascending=False)
        athlete_levels_years.dropna(subset=['CompYear'], inplace=True) # Remove levels if CompYear became NaN
        
        if athlete_levels_years.empty:
            st.warning(f"No valid level and competition year data available for athlete {athlete}.")
            st.stop()
            
        sorted_levels = athlete_levels_years.Level.tolist()
        selected_level = st.sidebar.selectbox("Choose Level", sorted_levels, index=0) # Defaults to most recent year's level
    else:
        st.warning(f"No data available for athlete {athlete}.") # Should ideally not be reached if df has data
        st.stop()
    
    show_current_year_only = st.sidebar.checkbox("Show most recent CompYear only", False)
    
    # Filter data by selected Level
    sub_level_data = sub[sub.Level == selected_level]

    if sub_level_data.empty:
        st.warning(f"No data available for {athlete} at Level {selected_level}.")
        st.stop()

    data_to_plot = sub_level_data.copy()
    
    if 'MeetDate' in data_to_plot.columns:
        data_to_plot['MeetDate'] = pd.to_datetime(data_to_plot['MeetDate'], errors='coerce')
        data_to_plot.dropna(subset=['MeetDate'], inplace=True)
    else:
        st.error("MeetDate column missing, cannot plot athlete data chronologically.")
        st.stop()

    if data_to_plot.empty: # Check if empty after potential dropna
        st.warning(f"No valid date data available for {athlete} at Level {selected_level}.")
        st.stop()

    current_comp_year_header_info = ""
    if show_current_year_only:
        if not data_to_plot.empty:
            # Ensure CompYear is numeric for max() if it's not already
            data_to_plot['CompYear'] = pd.to_numeric(data_to_plot['CompYear'], errors='coerce')
            most_recent_comp_year = data_to_plot.CompYear.max()
            data_to_plot = data_to_plot[data_to_plot.CompYear == most_recent_comp_year]
            current_comp_year_header_info = f" ({most_recent_comp_year})"
            # Convert CompYear to string for display consistency if it became numeric for filtering
            if 'CompYear' in data_to_plot.columns:
                 data_to_plot['CompYear'] = data_to_plot['CompYear'].astype(str)
        st.header(f"{athlete} - Level {selected_level}{current_comp_year_header_info}")
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
        event_data_for_plot = data_to_plot[data_to_plot.Event == event].copy() # Use .copy()
        
        st.subheader(event) # Display event title first

        if not event_data_for_plot.empty:
            # --- START: Stat Cards ---
            max_score_details = event_data_for_plot.loc[event_data_for_plot['Score'].idxmax()]
            max_score_val = max_score_details['Score']
            max_score_meet = max_score_details['MeetName']
            # Ensure max_score_year is taken from the specific row, could be string or number based on prior CompYear processing
            max_score_year = str(max_score_details['CompYear']) 
            
            median_score_val = event_data_for_plot['Score'].median()
            
            improvement_val = None
            improvement_delta_text = ""

            # Calculate improvement only if not showing current year only AND multiple years exist in event_data_for_plot for this level
            if not show_current_year_only and 'CompYear' in event_data_for_plot.columns and event_data_for_plot['CompYear'].nunique() > 1:
                # CompYear is already string in event_data_for_plot if multiple years are shown (due to data_to_plot processing)
                unique_comp_years_str = sorted(event_data_for_plot['CompYear'].unique(), key=lambda y_str: int(y_str), reverse=True)

                if len(unique_comp_years_str) >= 2:
                    latest_year_str = unique_comp_years_str[0]
                    previous_year_str = unique_comp_years_str[1]
                    
                    median_latest = event_data_for_plot[event_data_for_plot['CompYear'] == latest_year_str]['Score'].median()
                    median_previous = event_data_for_plot[event_data_for_plot['CompYear'] == previous_year_str]['Score'].median()
                    
                    if pd.notna(median_latest) and pd.notna(median_previous):
                        improvement_val = median_latest - median_previous
                        improvement_delta_text = f"Improvement (vs {previous_year_str})"

            num_cols = 2
            if improvement_val is not None:
                num_cols = 3
            
            cols = st.columns(num_cols)
            cols[0].metric(label="Max Score", value=f"{max_score_val:.3f}")
            cols[0].caption(f"Meet: {max_score_meet}, Year: {max_score_year}")
            cols[1].metric(label="Median Score", value=f"{median_score_val:.3f}")
            if improvement_val is not None:
                cols[2].metric(label=improvement_delta_text, value=f"{improvement_val:+.3f}", delta_color="normal")
            # --- END: Stat Cards ---

            # Sort by CompYear then MeetDate to ensure chronological stitching of year blocks
            # event_data_for_plot['CompYear'] is already string if multiple years, handle sorting carefully
            if 'CompYear' in event_data_for_plot.columns:
                 event_data_for_plot['CompYear_numeric'] = pd.to_numeric(event_data_for_plot['CompYear'])
                 event_data_for_plot = event_data_for_plot.sort_values(by=["CompYear_numeric", "MeetDate"])
                 event_data_for_plot.drop(columns=['CompYear_numeric'], inplace=True)
            else: # Should not happen if CompYear exists
                 event_data_for_plot = event_data_for_plot.sort_values(by=["MeetDate"])


            # Create a unique x-axis representation for each meet instance
            # Ensure CompYear is string for concatenation
            event_data_for_plot['CompYear_str'] = event_data_for_plot['CompYear'].astype(str)
            event_data_for_plot['x_display'] = event_data_for_plot['MeetName'] + ' (' + event_data_for_plot['CompYear_str'] + ')'
            
            current_y_axis_range = None
            if not fit_y_axis:
                if event == "All Around":
                    current_y_axis_range = [30.0, 40.0]
                else:
                    current_y_axis_range = [5.5, 10.0]
            
            plot_color_arg = "CompYear" if not show_current_year_only and event_data_for_plot.CompYear.nunique() > 1 else None
            
            discrete_color_sequence = [color_map.get(event, "black")] if plot_color_arg is None else None

            fig = px.line(event_data_for_plot, x="x_display", y="Score",
                            color=plot_color_arg,
                            markers=True, title="", # Title handled by st.subheader + stat cards
                            color_discrete_sequence=discrete_color_sequence,
                            text="Score")
            fig.update_layout(
                height=600,
                title_font_size=24,
                xaxis_title_font_size=18,
                xaxis_title="Meet (Year)",
                yaxis_title_font_size=18,
                legend_title_font_size=16,
                legend_font_size=14
            )
            fig.update_traces(line=dict(width=4), marker=dict(size=10), textposition="top center", texttemplate='%{text:.3f}')

            if not event_data_for_plot.empty:
                max_score_row_for_star = event_data_for_plot.loc[event_data_for_plot['Score'].idxmax()]
                fig.add_annotation(x=max_score_row_for_star['x_display'], y=max_score_row_for_star['Score'],
                                   text="⭐", showarrow=False, font=dict(size=20))

            if current_y_axis_range:
                fig.update_yaxes(range=current_y_axis_range)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # st.subheader(event) # Already called
            no_data_message = f"No data available for {event} at Level {selected_level}"
            if show_current_year_only and 'most_recent_comp_year' in locals() and most_recent_comp_year is not pd.NA:
                 no_data_message += f" in {int(most_recent_comp_year)}."
            else:
                 no_data_message += "."
            st.write(no_data_message)

    # --- START: Multi-Year Comparison Logic ---
    if not show_current_year_only: # Condition for attempting multi-year comparison
        # sub_level_data is the data for the current athlete at selected_level, all years
        # selected_level is the currently chosen level

        if not sub_level_data.empty:
            current_level = selected_level
            all_data_at_selected_level = sub_level_data.copy()

            if 'CompYear' in all_data_at_selected_level.columns:
                all_data_at_selected_level['CompYear_numeric'] = pd.to_numeric(all_data_at_selected_level['CompYear'], errors='coerce')
                all_data_at_selected_level.dropna(subset=['CompYear_numeric'], inplace=True)
                all_comp_years_at_this_level_numeric = sorted(all_data_at_selected_level.CompYear_numeric.unique())
            else:
                all_comp_years_at_this_level_numeric = []

            if len(all_comp_years_at_this_level_numeric) > 1:
                st.sidebar.markdown("---")
                st.sidebar.subheader(f"Multi-Year Meet Comparison (Level {current_level})")

                primary_comp_year_for_meets = int(all_comp_years_at_this_level_numeric[-1]) # Most recent year, as int

                meets_in_primary_year_at_level = sorted(
                    all_data_at_selected_level[
                        all_data_at_selected_level.CompYear_numeric == primary_comp_year_for_meets
                    ].MeetName.unique()
                )

                if meets_in_primary_year_at_level:
                    selected_comparison_meet = st.sidebar.selectbox(
                        f"Select Meet to Compare (from year {primary_comp_year_for_meets}, Level {current_level})",
                        meets_in_primary_year_at_level,
                        index=0,
                        key=f"multi_year_comparison_meet_{athlete}_{current_level}"
                    )

                    if selected_comparison_meet:
                        comparison_df = all_data_at_selected_level[
                            (all_data_at_selected_level.MeetName == selected_comparison_meet) &
                            (all_data_at_selected_level.CompYear_numeric.isin(all_comp_years_at_this_level_numeric))
                        ].copy() # Ensure it's a copy

                        if not comparison_df.empty and comparison_df.CompYear_numeric.nunique() > 1:
                            st.markdown("---")
                            st.header(f"Score Comparison: {selected_comparison_meet} (Level {current_level})")
                            
                            comparison_df['CompYear'] = comparison_df['CompYear_numeric'].astype(int).astype(str) # For display and coloring
                            sorted_comp_years_for_chart = sorted(comparison_df.CompYear.unique(), key=int)
                            
                            st.subheader(f"Comparing Years: {', '.join(sorted_comp_years_for_chart)}")
                            
                            events_order = ["Vault", "Bars", "Beam", "Floor", "All Around"]
                            comparison_df['Event'] = pd.Categorical(comparison_df['Event'], categories=events_order, ordered=True)
                            comparison_df = comparison_df.dropna(subset=['Event'])
                            comparison_df = comparison_df.sort_values('Event')

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
                                labels={"Score": "Score (AA / 4)", "Event": "Event", "CompYear": "Competition Year"},
                                text="Score",
                                category_orders={"CompYear": sorted_comp_years_for_chart}
                            )
                            fig_compare.update_traces(texttemplate='%{text:.3f}', textposition='outside')
                            fig_compare.update_layout(
                                yaxis_title="Score (AA scores are divided by 4)",
                                yaxis_range=[0.0, 10.5],
                                legend_title_text="Year",
                                height=500 
                            )
                            st.plotly_chart(fig_compare, use_container_width=True)
                        else:
                            st.info(f"Not enough data (multiple years) for {selected_comparison_meet} at Level {current_level} to compare.")
                else:
                    st.sidebar.info(f"No meets found in {primary_comp_year_for_meets} (most recent year at Level {current_level}) to enable comparison. Or, athlete did not participate in any single meet across multiple years at this level.")
            elif len(all_comp_years_at_this_level_numeric) == 1:
                st.sidebar.info(f"{athlete} has only competed at Level {current_level} in a single year ({int(all_comp_years_at_this_level_numeric[0])}). Multi-year meet comparison not available.")
            else:
                st.sidebar.info(f"{athlete} has no competition year data for Level {current_level}. Multi-year comparison not available.")
        # No 'else' needed here as sub_level_data.empty is caught when trying to plot line charts.

    # --- END: Multi-Year Comparison Logic ---

else:  # All athletes
    pool = df.groupby(["CompYear", "Event"]).Score.mean().reset_index()
    st.header("Entire Pool – Average Scores")
    st.plotly_chart(px.line(pool, x="CompYear", y="Score",
                            color="Event", markers=True))
