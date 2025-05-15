import sqlite3, pandas as pd, streamlit as st, plotly.express as px

st.title("TESTING DEPLOYMENT - NEW VERSION v5")

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

# Custom rounding function
def custom_round(value):
    if pd.isna(value) or not isinstance(value, (int, float)):
        return value # Return as is if NaN or not a number
    return round(value * 20) / 20

# ----- SIDEBAR DRILL-DOWN ----------------------------------------------------
view = st.sidebar.radio("View", ["All athletes", "By team", "By athlete"])

if view == "By team":
    selected_level_team = st.sidebar.selectbox("Choose team (Level)", sorted(df.Level.unique()), key="team_level_selector")
    calc_method_team = st.sidebar.radio("Calculation Method for Team Stats", ["Median", "Mean"], key="calc_method_team")
    
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
        
        st.subheader(event) # Display event title first

        if not event_data_for_team_year.empty:
            # Calculate average score per meet, ensuring chronological order by MeetDate
            if 'MeetDate' not in event_data_for_team_year.columns:
                st.error("MeetDate column is missing, cannot guarantee chronological order for meets.")
                avg_event_scores = event_data_for_team_year.groupby("MeetName", as_index=False).Score.mean()
            else:
                avg_event_scores = event_data_for_team_year.groupby(["MeetName", "MeetDate"], as_index=False).Score.mean()
                avg_event_scores = avg_event_scores.sort_values(by="MeetDate")

            if not avg_event_scores.empty:
                # --- START: Team Stat Cards ---
                team_max_score_details = avg_event_scores.loc[avg_event_scores['Score'].idxmax()]
                team_max_score_val = custom_round(team_max_score_details['Score'])
                team_max_score_meet = team_max_score_details['MeetName']
                
                team_chosen_stat_val = None
                team_chosen_stat_label = ""
                if calc_method_team == "Median":
                    team_chosen_stat_val = custom_round(avg_event_scores['Score'].median())
                    team_chosen_stat_label = "Median Team Score"
                else: # Mean
                    team_chosen_stat_val = custom_round(avg_event_scores['Score'].mean())
                    team_chosen_stat_label = "Mean Team Score"

                team_trend_val = None
                team_trend_label = "Intra-Year Team Trend"

                num_meets_for_trend = len(avg_event_scores)
                if num_meets_for_trend < 2:
                    team_trend_val = "N/A"
                else:
                    team_scores_series = avg_event_scores['Score']
                    first_period_scores = pd.Series(dtype=float)
                    second_period_scores = pd.Series(dtype=float)

                    if num_meets_for_trend % 2 == 0:
                        first_period_scores = team_scores_series.iloc[:num_meets_for_trend//2]
                        second_period_scores = team_scores_series.iloc[num_meets_for_trend//2:]
                    else:
                        middle_idx = num_meets_for_trend // 2
                        first_period_scores = team_scores_series.iloc[:middle_idx + 1]
                        second_period_scores = team_scores_series.iloc[middle_idx:]
                    
                    if first_period_scores.empty or first_period_scores.isnull().all() or \
                       second_period_scores.empty or second_period_scores.isnull().all():
                        team_trend_val = "N/A"
                    else:
                        stat_first_period = custom_round(first_period_scores.median() if calc_method_team == "Median" else first_period_scores.mean())
                        stat_second_period = custom_round(second_period_scores.median() if calc_method_team == "Median" else second_period_scores.mean())

                        if pd.notna(stat_first_period) and pd.notna(stat_second_period):
                            calculated_team_trend = stat_second_period - stat_first_period
                            team_trend_val = f"{custom_round(calculated_team_trend):+.2f}"
                        else:
                            team_trend_val = "N/A"
                
                team_stat_cols = st.columns(3)
                team_stat_cols[0].metric(label="Max Team Score", value=f"{team_max_score_val:.2f}")
                team_stat_cols[0].caption(f"Meet: {team_max_score_meet}")
                team_stat_cols[1].metric(label=team_chosen_stat_label, value=f"{team_chosen_stat_val:.2f}")
                team_stat_cols[2].metric(label=team_trend_label, value=str(team_trend_val), delta_color="off")
                # --- END: Team Stat Cards ---
                
                current_y_axis_range = None
                if event == "All Around":
                    current_y_axis_range = [30.0, 40.0] 
                else:
                    current_y_axis_range = [5.5, 10.0]
            
                fig = px.line(avg_event_scores, x="MeetName", y="Score", 
                                markers=True, title="", # Removed specific title
                                color_discrete_sequence=[color_map.get(event, "black")],
                                text="Score")
                
                fig.update_layout(
                    height=600,
                    title_font_size=24,
                    xaxis_title_font_size=18,
                    yaxis_title_font_size=18,
                    legend_title_font_size=16, 
                    legend_font_size=14
                )
                # Round plotted scores (text on graph) to two decimal places
                fig.update_traces(line=dict(width=4), marker=dict(size=10), textposition="top center", texttemplate='%{text:.2f}')

                if not avg_event_scores.empty:
                    max_score_row = avg_event_scores.loc[avg_event_scores['Score'].idxmax()]
                    fig.add_annotation(x=max_score_row['MeetName'], y=max_score_row['Score'],
                                       text="⭐", showarrow=False, font=dict(size=20))

                if current_y_axis_range:
                    fig.update_yaxes(range=current_y_axis_range)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                # st.subheader(event) # Already called
                st.write(f"No average score data available for {event} for Level {selected_level_team} in {selected_year}.")
        else:
            # st.subheader(event) # Already called
            st.write(f"No data available for {event} for Level {selected_level_team} in {selected_year}.")

elif view == "By athlete":
    athlete = st.sidebar.selectbox("Choose athlete", sorted(df.AthleteName.unique()))
    sub     = df[df.AthleteName == athlete]

    if not sub.empty:
        athlete_levels_years = sub.groupby('Level')['CompYear'].max().reset_index()
        athlete_levels_years['CompYear'] = pd.to_numeric(athlete_levels_years['CompYear'], errors='coerce')
        athlete_levels_years = athlete_levels_years.sort_values(by='CompYear', ascending=False)
        athlete_levels_years.dropna(subset=['CompYear'], inplace=True) 
        
        if athlete_levels_years.empty:
            st.warning(f"No valid level and competition year data available for athlete {athlete}.")
            st.stop()
            
        sorted_levels = athlete_levels_years.Level.tolist()
        selected_level = st.sidebar.selectbox("Choose Level", sorted_levels, index=0) 
    else:
        st.warning(f"No data available for athlete {athlete}.") 
        st.stop()
    
    show_current_year_only = st.sidebar.checkbox("Show most recent CompYear only", False)
    
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

    if data_to_plot.empty: 
        st.warning(f"No valid date data available for {athlete} at Level {selected_level}.")
        st.stop()

    current_comp_year_header_info = ""
    if show_current_year_only:
        if not data_to_plot.empty:
            data_to_plot['CompYear'] = pd.to_numeric(data_to_plot['CompYear'], errors='coerce')
            most_recent_comp_year_val = data_to_plot.CompYear.max() # Keep as numeric for filtering
            data_to_plot = data_to_plot[data_to_plot.CompYear == most_recent_comp_year_val]
            current_comp_year_header_info = f" ({int(most_recent_comp_year_val)})" if pd.notna(most_recent_comp_year_val) else ""
            if 'CompYear' in data_to_plot.columns:
                 data_to_plot['CompYear'] = data_to_plot['CompYear'].astype(str) # Convert back to string for display consistency
        st.header(f"{athlete} - Level {selected_level}{current_comp_year_header_info}")
    else:
        st.header(f"{athlete} - Level {selected_level} (All Years)")
        if 'CompYear' in data_to_plot.columns:
            data_to_plot['CompYear'] = data_to_plot['CompYear'].astype(str)

    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", False)
    calc_method = st.sidebar.radio("Calculation Method for Stats", ["Median", "Mean"], key="calc_method_athlete")
    y_axis_range = None

    events = ["Vault", "Bars", "Beam", "Floor", "All Around"]
    
    for event in events:
        event_data_for_plot = data_to_plot[data_to_plot.Event == event].copy() 
        
        st.subheader(event) 

        if not event_data_for_plot.empty:
            # --- START: Stat Cards Calculations (Athlete) ---
            max_score_details_athlete = event_data_for_plot.loc[event_data_for_plot['Score'].idxmax()]
            max_score_val_athlete = custom_round(max_score_details_athlete['Score'])
            max_score_meet_athlete = max_score_details_athlete['MeetName']
            max_score_year_athlete = str(max_score_details_athlete['CompYear']) 
            
            chosen_stat_val_athlete = None
            chosen_stat_label_athlete = ""
            if calc_method == "Median":
                chosen_stat_val_athlete = custom_round(event_data_for_plot['Score'].median())
                chosen_stat_label_athlete = "Median Score"
            else: # Mean
                chosen_stat_val_athlete = custom_round(event_data_for_plot['Score'].mean())
                chosen_stat_label_athlete = "Mean Score"
            
            improvement_val_numeric_athlete = None 
            improvement_display_text_athlete = "" 
            improvement_label_athlete = ""

            is_multi_year_scenario_for_comparison_athlete = (
                not show_current_year_only and 
                'CompYear' in event_data_for_plot.columns and 
                event_data_for_plot['CompYear'].nunique() > 1
            )
            
            effective_comp_years_for_event_athlete = event_data_for_plot['CompYear'].unique()
            is_effectively_single_year_view_for_event_athlete = show_current_year_only or (len(effective_comp_years_for_event_athlete) == 1)

            if is_multi_year_scenario_for_comparison_athlete:
                improvement_label_athlete = "Improvement" 
                unique_comp_years_str_athlete = sorted(event_data_for_plot['CompYear'].unique(), key=lambda y_str: int(y_str), reverse=True)

                if len(unique_comp_years_str_athlete) >= 2: 
                    latest_year_str_athlete = unique_comp_years_str_athlete[0]
                    previous_year_str_athlete = unique_comp_years_str_athlete[1]
                    
                    stat_latest_athlete = None
                    stat_previous_athlete = None
                    if calc_method == "Median":
                        stat_latest_athlete = event_data_for_plot[event_data_for_plot['CompYear'] == latest_year_str_athlete]['Score'].median()
                        stat_previous_athlete = event_data_for_plot[event_data_for_plot['CompYear'] == previous_year_str_athlete]['Score'].median()
                    else: # Mean
                        stat_latest_athlete = event_data_for_plot[event_data_for_plot['CompYear'] == latest_year_str_athlete]['Score'].mean()
                        stat_previous_athlete = event_data_for_plot[event_data_for_plot['CompYear'] == previous_year_str_athlete]['Score'].mean()
                    
                    if pd.notna(stat_latest_athlete) and pd.notna(stat_previous_athlete):
                        improvement_val_numeric_athlete = custom_round(stat_latest_athlete - stat_previous_athlete)
                        improvement_label_athlete = f"Improvement (vs {previous_year_str_athlete})"
                    else:
                        improvement_val_numeric_athlete = "N/A" # Mark as N/A if calculation fails
                        improvement_label_athlete = f"Improvement (vs {previous_year_str_athlete}, N/A)"
            
            elif is_effectively_single_year_view_for_event_athlete and not event_data_for_plot.empty:
                improvement_label_athlete = "Intra-Year Trend"
                if 'MeetDate' not in event_data_for_plot.columns:
                    improvement_val_numeric_athlete = "N/A (No MeetDate)"
                else:
                    year_event_scores_for_trend_athlete = event_data_for_plot.sort_values(by="MeetDate")
                    num_meets_athlete = len(year_event_scores_for_trend_athlete)

                    if num_meets_athlete < 2:
                        improvement_val_numeric_athlete = "N/A" 
                    else:
                        scores_series_athlete = year_event_scores_for_trend_athlete['Score']
                        first_period_scores_data_athlete = pd.Series(dtype=float)
                        second_period_scores_data_athlete = pd.Series(dtype=float)

                        if num_meets_athlete % 2 == 0: 
                            first_period_scores_data_athlete = scores_series_athlete.iloc[:num_meets_athlete//2]
                            second_period_scores_data_athlete = scores_series_athlete.iloc[num_meets_athlete//2:]
                        else: 
                            middle_idx_athlete = num_meets_athlete // 2 
                            first_period_scores_data_athlete = scores_series_athlete.iloc[:middle_idx_athlete + 1]
                            second_period_scores_data_athlete = scores_series_athlete.iloc[middle_idx_athlete:]
                        
                        if first_period_scores_data_athlete.empty or first_period_scores_data_athlete.isnull().all() or \
                           second_period_scores_data_athlete.empty or second_period_scores_data_athlete.isnull().all():
                            improvement_val_numeric_athlete = "N/A"
                        else:
                            stat_first_athlete = None
                            stat_second_athlete = None
                            if calc_method == "Median":
                                stat_first_athlete = first_period_scores_data_athlete.median()
                                stat_second_athlete = second_period_scores_data_athlete.median()
                            else: # Mean
                                stat_first_athlete = first_period_scores_data_athlete.mean()
                                stat_second_athlete = second_period_scores_data_athlete.mean()
                            
                            if pd.notna(stat_first_athlete) and pd.notna(stat_second_athlete):
                                improvement_val_numeric_athlete = custom_round(stat_second_athlete - stat_first_athlete)
                            else:
                                improvement_val_numeric_athlete = "N/A" 
            
            # --- END: Stat Cards Calculations (Athlete) ---

            # --- START: Stat Cards Display (Athlete) ---
            athlete_stat_cols = st.columns(3)
            athlete_stat_cols[0].metric(label="Max Score", value=f"{max_score_val_athlete:.2f}")
            athlete_stat_cols[0].caption(f"Meet: {max_score_meet_athlete}, Year: {max_score_year_athlete}")
            athlete_stat_cols[1].metric(label=chosen_stat_label_athlete, value=f"{chosen_stat_val_athlete:.2f}")
            
            if improvement_val_numeric_athlete is not None:
                display_value_for_metric_athlete = ""
                if isinstance(improvement_val_numeric_athlete, (float, int)): 
                    display_value_for_metric_athlete = f"{improvement_val_numeric_athlete:+.2f}"
                else: # It's "N/A" or other string
                    display_value_for_metric_athlete = str(improvement_val_numeric_athlete)
                
                current_delta_label_athlete = improvement_label_athlete if improvement_label_athlete else "Trend/Improvement"
                athlete_stat_cols[2].metric(label=current_delta_label_athlete, value=display_value_for_metric_athlete, delta_color="off")
            # --- END: Stat Cards Display (Athlete) ---

            if 'CompYear' in event_data_for_plot.columns:
                 event_data_for_plot['CompYear_numeric'] = pd.to_numeric(event_data_for_plot['CompYear'])
                 event_data_for_plot = event_data_for_plot.sort_values(by=["CompYear_numeric", "MeetDate"])
                 event_data_for_plot.drop(columns=['CompYear_numeric'], inplace=True)
            else: 
                 event_data_for_plot = event_data_for_plot.sort_values(by=["MeetDate"])

            event_data_for_plot['CompYear_str'] = event_data_for_plot['CompYear'].astype(str)
            event_data_for_plot['x_display'] = event_data_for_plot['MeetName'] + ' (' + event_data_for_plot['CompYear_str'] + ')'
            
            current_y_axis_range_athlete = None
            if not fit_y_axis:
                if event == "All Around":
                    current_y_axis_range_athlete = [30.0, 40.0]
                else:
                    current_y_axis_range_athlete = [5.5, 10.0]
            
            plot_color_arg_athlete = "CompYear" if not show_current_year_only and event_data_for_plot.CompYear.nunique() > 1 else None
            
            discrete_color_sequence_athlete = [color_map.get(event, "black")] if plot_color_arg_athlete is None else None

            fig_athlete = px.line(event_data_for_plot, x="x_display", y="Score",
                            color=plot_color_arg_athlete,
                            markers=True, title="", # Title removed
                            color_discrete_sequence=discrete_color_sequence_athlete,
                            text="Score")
            fig_athlete.update_layout(
                height=600,
                title_font_size=24,
                xaxis_title_font_size=18,
                xaxis_title="Meet (Year)",
                yaxis_title_font_size=18,
                legend_title_font_size=16,
                legend_font_size=14
            )
            # Athlete text template already had .3f, let's make it consistent or decide if it needs rounding.
            # For now, keeping athlete's plotted text at .3f as per original structure.
            fig_athlete.update_traces(line=dict(width=4), marker=dict(size=10), textposition="top center", texttemplate='%{text:.3f}')


            if not event_data_for_plot.empty:
                max_score_row_for_star_athlete = event_data_for_plot.loc[event_data_for_plot['Score'].idxmax()]
                fig_athlete.add_annotation(x=max_score_row_for_star_athlete['x_display'], y=max_score_row_for_star_athlete['Score'],
                                   text="⭐", showarrow=False, font=dict(size=20))

            if current_y_axis_range_athlete:
                fig_athlete.update_yaxes(range=current_y_axis_range_athlete)
            st.plotly_chart(fig_athlete, use_container_width=True)
        else:
            no_data_message_athlete = f"No data available for {event} at Level {selected_level}"
            if show_current_year_only and 'most_recent_comp_year_val' in locals() and pd.notna(most_recent_comp_year_val):
                 no_data_message_athlete += f" in {int(most_recent_comp_year_val)}."
            else:
                 no_data_message_athlete += "."
            st.write(no_data_message_athlete)

    # --- START: Multi-Year Comparison Logic ---
    if not show_current_year_only: 
        if not sub_level_data.empty:
            current_level_athlete = selected_level
            all_data_at_selected_level_athlete = sub_level_data.copy()

            if 'CompYear' in all_data_at_selected_level_athlete.columns:
                all_data_at_selected_level_athlete['CompYear_numeric'] = pd.to_numeric(all_data_at_selected_level_athlete['CompYear'], errors='coerce')
                all_data_at_selected_level_athlete.dropna(subset=['CompYear_numeric'], inplace=True)
                all_comp_years_at_this_level_numeric_athlete = sorted(all_data_at_selected_level_athlete.CompYear_numeric.unique())
            else:
                all_comp_years_at_this_level_numeric_athlete = []

            if len(all_comp_years_at_this_level_numeric_athlete) > 1:
                st.sidebar.markdown("---")
                st.sidebar.subheader(f"Multi-Year Meet Comparison (Level {current_level_athlete})")

                primary_comp_year_for_meets_athlete = int(all_comp_years_at_this_level_numeric_athlete[-1]) 

                meets_in_primary_year_at_level_athlete = sorted(
                    all_data_at_selected_level_athlete[
                        all_data_at_selected_level_athlete.CompYear_numeric == primary_comp_year_for_meets_athlete
                    ].MeetName.unique()
                )

                if meets_in_primary_year_at_level_athlete:
                    selected_comparison_meet_athlete = st.sidebar.selectbox(
                        f"Select Meet to Compare (from year {primary_comp_year_for_meets_athlete}, Level {current_level_athlete})",
                        meets_in_primary_year_at_level_athlete,
                        index=0,
                        key=f"multi_year_comparison_meet_{athlete}_{current_level_athlete}"
                    )

                    if selected_comparison_meet_athlete:
                        comparison_df_athlete = all_data_at_selected_level_athlete[
                            (all_data_at_selected_level_athlete.MeetName == selected_comparison_meet_athlete) &
                            (all_data_at_selected_level_athlete.CompYear_numeric.isin(all_comp_years_at_this_level_numeric_athlete))
                        ].copy() 

                        if not comparison_df_athlete.empty and comparison_df_athlete.CompYear_numeric.nunique() > 1:
                            st.markdown("---")
                            st.header(f"Score Comparison: {selected_comparison_meet_athlete} (Level {current_level_athlete})")
                            
                            comparison_df_athlete['CompYear'] = comparison_df_athlete['CompYear_numeric'].astype(int).astype(str) 
                            sorted_comp_years_for_chart_athlete = sorted(comparison_df_athlete.CompYear.unique(), key=int)
                            
                            st.subheader(f"Comparing Years: {', '.join(sorted_comp_years_for_chart_athlete)}")
                            
                            events_order_athlete = ["Vault", "Bars", "Beam", "Floor", "All Around"]
                            comparison_df_athlete['Event'] = pd.Categorical(comparison_df_athlete['Event'], categories=events_order_athlete, ordered=True)
                            comparison_df_athlete = comparison_df_athlete.dropna(subset=['Event'])
                            comparison_df_athlete = comparison_df_athlete.sort_values('Event')

                            if 'All Around' in comparison_df_athlete['Event'].values:
                                aa_condition_athlete = comparison_df_athlete['Event'] == 'All Around'
                                comparison_df_athlete.loc[aa_condition_athlete, 'Score'] = comparison_df_athlete.loc[aa_condition_athlete, 'Score'] / 4
                            
                            fig_compare_athlete = px.bar(
                                comparison_df_athlete,
                                x="Event",
                                y="Score",
                                color="CompYear",
                                barmode="group",
                                title=f"Event Scores at {selected_comparison_meet_athlete} (Level {current_level_athlete})", # Title kept for bar chart
                                labels={"Score": "Score (AA / 4)", "Event": "Event", "CompYear": "Competition Year"},
                                text="Score",
                                category_orders={"CompYear": sorted_comp_years_for_chart_athlete}
                            )
                            fig_compare_athlete.update_traces(texttemplate='%{text:.3f}', textposition='outside') # AA can be .25, so .3f is fine
                            fig_compare_athlete.update_layout(
                                yaxis_title="Score (AA scores are divided by 4)",
                                yaxis_range=[0.0, 10.5],
                                legend_title_text="Year",
                                height=500 
                            )
                            st.plotly_chart(fig_compare_athlete, use_container_width=True)
                        else:
                            st.info(f"Not enough data (multiple years) for {selected_comparison_meet_athlete} at Level {current_level_athlete} to compare.")
                else:
                    st.sidebar.info(f"No meets found in {primary_comp_year_for_meets_athlete} (most recent year at Level {current_level_athlete}) to enable comparison. Or, athlete did not participate in any single meet across multiple years at this level.")
            elif len(all_comp_years_at_this_level_numeric_athlete) == 1:
                st.sidebar.info(f"{athlete} has only competed at Level {current_level_athlete} in a single year ({int(all_comp_years_at_this_level_numeric_athlete[0])}). Multi-year meet comparison not available.")
            else:
                st.sidebar.info(f"{athlete} has no competition year data for Level {current_level_athlete}. Multi-year comparison not available.")

else:  # All athletes
    pool = df.groupby(["CompYear", "Event"]).Score.mean().reset_index()
    st.header("Entire Pool – Average Scores")
    st.plotly_chart(px.line(pool, x="CompYear", y="Score",
                            color="Event", markers=True))
