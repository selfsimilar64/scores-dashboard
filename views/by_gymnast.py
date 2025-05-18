import streamlit as st
import pandas as pd
import plotly.express as px
from utils.maths import custom_round
from config import (
    EVENT_COLORS, 
    DEFAULT_Y_RANGE, 
    COMMON_LAYOUT_ARGS, 
    COMMON_LINE_TRACE_ARGS,
    COMPARISON_BAR_Y_RANGE,
    COMMON_BAR_TRACE_ARGS,
    EVENTS_ORDER,
    CALC_METHODS,
    DEFAULT_CALC_METHOD_ATHLETE,
    DEFAULT_SHOW_CURRENT_YEAR_ONLY,
    DEFAULT_FIT_Y_AXIS_ATHLETE,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE,
    STAR_ANNOTATION_FONT_SIZE,
    CUSTOM_TAB_CSS
)

def create_gymnast_top_scores_table(df: pd.DataFrame, selected_athlete: str, selected_level: str, show_current_year_only: bool, most_recent_comp_year: int | None):
    """Creates and displays a table of top 5 scores for a given gymnast, level, and year selection."""
    data_for_table = df[(df.AthleteName == selected_athlete) & (df.Level == selected_level)].copy()

    title_year_segment = ""
    if show_current_year_only and most_recent_comp_year is not None:
        data_for_table = data_for_table[data_for_table.CompYear == most_recent_comp_year]
        title_year_segment = f" - {most_recent_comp_year}"
    elif show_current_year_only and most_recent_comp_year is None:
        # This case implies no data for the most recent year if one was determined, or no CompYear data at all.
        # Fallback to all years for the athlete/level or show specific message.
        st.caption(f"Top scores table: Most recent year selected, but no CompYear found for {selected_athlete} at Level {selected_level}.")
        # data_for_table remains as is (all years for athlete/level)

    # Exclude "All Around" scores and sort by score
    data_for_table = data_for_table[data_for_table.Event != "All Around"]
    top_scores = data_for_table.sort_values(by="Score", ascending=False).head(5)

    if top_scores.empty:
        st.caption(f"No top scores data available for {selected_athlete} at Level {selected_level}{title_year_segment} (excluding All Around).")
        return

    # Select and rename columns, omitting AthleteName
    table_data = top_scores[["MeetName", "CompYear", "Place", "Score"]].copy()
    table_data['CompYear'] = table_data['CompYear'].astype(str)
    table_data['Place'] = table_data['Place'].astype(str)
    try:
        table_data['Place'] = pd.to_numeric(table_data['Place'], errors='coerce').fillna(0).astype(int)
    except ValueError:
        pass # Keep as string
    table_data['Score'] = table_data['Score'].apply(lambda x: f"{x:.3f}")

    st.subheader(f"Top 5 Scores for {selected_athlete} (Level {selected_level}{title_year_segment}, Excluding All Around)")
    st.table(table_data)


def render_by_gymnast_view(df: pd.DataFrame):
    st.sidebar.header("Gymnast View Options") # Added header for clarity
    st.markdown(CUSTOM_TAB_CSS, unsafe_allow_html=True) # Apply custom tab styles for tabs

    col1_gymnast, col2_gymnast = st.columns(2)
    with col1_gymnast:
        athlete_names = sorted(df.AthleteName.unique())
        if not athlete_names:
            st.warning("No athlete data available.")
            return
        athlete = st.selectbox("Choose athlete", athlete_names, key="main_athlete_selector")
    
    sub = df[df.AthleteName == athlete]
    selected_level = None

    if not sub.empty:
        athlete_levels_years = sub.groupby('Level')['CompYear'].max().reset_index()
        athlete_levels_years['CompYear'] = pd.to_numeric(athlete_levels_years['CompYear'], errors='coerce')
        athlete_levels_years = athlete_levels_years.sort_values(by='CompYear', ascending=False)
        athlete_levels_years.dropna(subset=['CompYear'], inplace=True)
        
        if athlete_levels_years.empty:
            st.warning(f"No valid level and competition year data available for athlete {athlete}.")
            # Displaying for selected athlete, so don't return globally, allow level selection if possible
        else:
            sorted_levels = athlete_levels_years.Level.tolist()
            with col2_gymnast:
                selected_level = st.selectbox("Choose Level", sorted_levels, index=0, key="main_gymnast_level_selector")
    else:
        st.warning(f"No data available for athlete {athlete}.") 
        return
    
    if selected_level is None: # Could happen if athlete_levels_years was empty
        st.warning(f"No levels found for {athlete}. Please select another athlete or check data.")
        return

    show_current_year_only = st.sidebar.checkbox(
        "Show most recent CompYear only", 
        DEFAULT_SHOW_CURRENT_YEAR_ONLY, 
        key="gymnast_show_current_year"
    )
    fit_y_axis = st.sidebar.checkbox(
        "Fit Y-axis to data", 
        DEFAULT_FIT_Y_AXIS_ATHLETE, 
        key="gymnast_fit_y_axis"
    )
    calc_method = st.sidebar.radio(
        "Calculation Method for Stats", 
        CALC_METHODS, 
        index=CALC_METHODS.index(DEFAULT_CALC_METHOD_ATHLETE),
        key="calc_method_athlete"
    )
    
    sub_level_data = sub[sub.Level == selected_level]
    if sub_level_data.empty:
        st.warning(f"No data available for {athlete} at Level {selected_level}.")
        return

    data_to_plot = sub_level_data.copy()
    if 'MeetDate' not in data_to_plot.columns:
        st.error("MeetDate column missing, cannot plot athlete data chronologically.")
        return
        
    data_to_plot['MeetDate'] = pd.to_datetime(data_to_plot['MeetDate'], errors='coerce')
    data_to_plot.dropna(subset=['MeetDate'], inplace=True)

    if data_to_plot.empty:
        st.warning(f"No valid date data available for {athlete} at Level {selected_level}.")
        return

    most_recent_comp_year_val = None
    temp_data_for_year_check = sub_level_data.copy()
    if 'CompYear' in temp_data_for_year_check.columns:
        temp_data_for_year_check['CompYear_numeric'] = pd.to_numeric(temp_data_for_year_check['CompYear'], errors='coerce')
        if not temp_data_for_year_check.CompYear_numeric.empty and temp_data_for_year_check.CompYear_numeric.notna().any():
            most_recent_comp_year_val = int(temp_data_for_year_check.CompYear_numeric.max())

    if show_current_year_only and most_recent_comp_year_val is not None:
        data_to_plot = data_to_plot[data_to_plot.CompYear == most_recent_comp_year_val]
        if 'CompYear' in data_to_plot.columns: # Ensure it still exists
             data_to_plot['CompYear'] = data_to_plot['CompYear'].astype(str)
    elif show_current_year_only and most_recent_comp_year_val is None:
        # If 'show current year only' is ticked but we couldn't determine a most_recent_comp_year_val
        # (e.g. CompYear column is all NaN or empty after filtering for level),
        # data_to_plot will contain all years for that level.
        # We can add a note or proceed; for now, proceed, table will show data from all years for level.
        pass 

    # --- Display Top Scores Table ---
    st.markdown("---") # Visual separator
    # Pass the original df, selected athlete/level, and year filtering info to the table function
    # The table function will internally filter by year if show_current_year_only is True and a year is found.
    create_gymnast_top_scores_table(sub_level_data, athlete, selected_level, show_current_year_only, most_recent_comp_year_val)
    st.markdown("---") # Visual separator before event tabs

    event_tabs_gymnast = st.tabs(EVENTS_ORDER)

    for i, event in enumerate(EVENTS_ORDER):
        with event_tabs_gymnast[i]:
            event_data_for_plot = data_to_plot[data_to_plot.Event == event].copy()
            
            if not event_data_for_plot.empty:
                max_score_details_athlete = event_data_for_plot.loc[event_data_for_plot['Score'].idxmax()]
                max_score_val_athlete = custom_round(max_score_details_athlete['Score'])
                # max_score_meet_athlete = max_score_details_athlete['MeetName'] # Caption removed
                # max_score_year_athlete = str(max_score_details_athlete['CompYear']) # Caption removed
                
                chosen_stat_val_athlete = custom_round(event_data_for_plot['Score'].median() if calc_method == "Median" else event_data_for_plot['Score'].mean())
                chosen_stat_label_athlete = f"{calc_method} Score"
                
                improvement_val_numeric_athlete = None 
                improvement_label_athlete = ""

                # Ensure CompYear is present and numeric for comparisons
                if 'CompYear' in event_data_for_plot.columns:
                    event_data_for_plot['CompYear_numeric_temp'] = pd.to_numeric(event_data_for_plot['CompYear'], errors='coerce')
                    unique_comp_years_numeric = sorted(event_data_for_plot['CompYear_numeric_temp'].dropna().unique(), reverse=True)
                else:
                    unique_comp_years_numeric = []

                is_multi_year_scenario_for_comparison_athlete = (
                    not show_current_year_only and 
                    len(unique_comp_years_numeric) > 1
                )
                
                is_effectively_single_year_view_for_event_athlete = show_current_year_only or (len(unique_comp_years_numeric) <= 1)

                if is_multi_year_scenario_for_comparison_athlete:
                    latest_year_numeric = unique_comp_years_numeric[0]
                    previous_year_numeric = unique_comp_years_numeric[1]
                    
                    latest_year_scores = event_data_for_plot[event_data_for_plot['CompYear_numeric_temp'] == latest_year_numeric]['Score']
                    previous_year_scores = event_data_for_plot[event_data_for_plot['CompYear_numeric_temp'] == previous_year_numeric]['Score']

                    stat_latest_athlete = custom_round(latest_year_scores.median() if calc_method == "Median" else latest_year_scores.mean())
                    stat_previous_athlete = custom_round(previous_year_scores.median() if calc_method == "Median" else previous_year_scores.mean())
                    
                    if pd.notna(stat_latest_athlete) and pd.notna(stat_previous_athlete):
                        improvement_val_numeric_athlete = custom_round(stat_latest_athlete - stat_previous_athlete)
                        improvement_label_athlete = f"Improvement (vs {int(previous_year_numeric)})"
                    else:
                        improvement_val_numeric_athlete = "N/A"
                        improvement_label_athlete = f"Improvement (vs {int(previous_year_numeric)} N/A)"
                
                elif is_effectively_single_year_view_for_event_athlete and not event_data_for_plot.empty:
                    improvement_label_athlete = "Intra-Year Trend"
                    if 'MeetDate' not in event_data_for_plot.columns:
                        improvement_val_numeric_athlete = "N/A (No MeetDate)"
                    else:
                        year_event_scores_for_trend_athlete = event_data_for_plot.sort_values(by="MeetDate").reset_index(drop=True)
                        num_meets_athlete = len(year_event_scores_for_trend_athlete)

                        if num_meets_athlete < 2:
                            improvement_val_numeric_athlete = "N/A" 
                        else:
                            scores_series_athlete = year_event_scores_for_trend_athlete['Score']
                            middle_idx_athlete = num_meets_athlete // 2
                            first_period_scores_data_athlete = scores_series_athlete.iloc[:middle_idx_athlete + (num_meets_athlete % 2)]
                            second_period_scores_data_athlete = scores_series_athlete.iloc[middle_idx_athlete:]
                            
                            if first_period_scores_data_athlete.empty or first_period_scores_data_athlete.isnull().all() or \
                               second_period_scores_data_athlete.empty or second_period_scores_data_athlete.isnull().all():
                                improvement_val_numeric_athlete = "N/A"
                            else:
                                stat_first_athlete = custom_round(first_period_scores_data_athlete.median() if calc_method == "Median" else first_period_scores_data_athlete.mean())
                                stat_second_athlete = custom_round(second_period_scores_data_athlete.median() if calc_method == "Median" else second_period_scores_data_athlete.mean())
                                
                                if pd.notna(stat_first_athlete) and pd.notna(stat_second_athlete):
                                    improvement_val_numeric_athlete = custom_round(stat_second_athlete - stat_first_athlete)
                                else:
                                    improvement_val_numeric_athlete = "N/A"
                if 'CompYear_numeric_temp' in event_data_for_plot.columns: # Clean up temp column
                    event_data_for_plot.drop(columns=['CompYear_numeric_temp'], inplace=True)
                
                athlete_stat_cols = st.columns(3)
                with athlete_stat_cols[0]:
                    st.metric(label="Max Score", value=f"{max_score_val_athlete:.3f}")
                    # Caption removed as per original app.py changes
                with athlete_stat_cols[1]:
                    st.metric(label=chosen_stat_label_athlete, value=f"{chosen_stat_val_athlete:.3f}")
                    st.caption("\u00A0")
                with athlete_stat_cols[2]:
                    display_value_for_metric_athlete = f"{improvement_val_numeric_athlete:+.3f}" if isinstance(improvement_val_numeric_athlete, (float, int)) else str(improvement_val_numeric_athlete)
                    current_delta_label_athlete = improvement_label_athlete if improvement_label_athlete else "Trend/Improvement"
                    st.metric(label=current_delta_label_athlete, value=display_value_for_metric_athlete, delta_color="off")
                    st.caption("\u00A0")

                # Prepare data for plotting
                if 'CompYear' in event_data_for_plot.columns:
                     event_data_for_plot['CompYear_numeric'] = pd.to_numeric(event_data_for_plot['CompYear'], errors='coerce')
                     event_data_for_plot = event_data_for_plot.sort_values(by=["CompYear_numeric", "MeetDate"])
                     event_data_for_plot.drop(columns=['CompYear_numeric'], inplace=True, errors='ignore') # Add errors='ignore'
                else: 
                     event_data_for_plot = event_data_for_plot.sort_values(by=["MeetDate"])

                event_data_for_plot['CompYear_str'] = event_data_for_plot['CompYear'].astype(str)
                event_data_for_plot['x_display'] = event_data_for_plot['MeetName'] + ' (' + event_data_for_plot['CompYear_str'] + ')'
                
                current_y_axis_range_athlete = None
                if not fit_y_axis:
                    current_y_axis_range_athlete = DEFAULT_Y_RANGE.all_around if event == "All Around" else DEFAULT_Y_RANGE.event
                
                plot_color_arg_athlete = "CompYear" if not show_current_year_only and event_data_for_plot.CompYear.nunique() > 1 else None
                discrete_color_sequence_athlete = [EVENT_COLORS.get(event, "black")] if plot_color_arg_athlete is None else None

                fig_athlete = px.line(event_data_for_plot, x="x_display", y="Score",
                                color=plot_color_arg_athlete,
                                markers=True,
                                color_discrete_sequence=discrete_color_sequence_athlete,
                                text="Score")
                
                fig_athlete.update_layout(
                    **COMMON_LAYOUT_ARGS, 
                    xaxis_title="Meet (Year)",
                    xaxis=dict(tickfont=dict(size=XAXIS_TICKFONT_SIZE)),
                    yaxis=dict(tickfont=dict(size=YAXIS_TICKFONT_SIZE))
                )
                fig_athlete.update_traces(
                    **COMMON_LINE_TRACE_ARGS, 
                    texttemplate='%{text:.3f}',
                    textfont=dict(size=MARKER_TEXTFONT_SIZE)
                )

                if not event_data_for_plot.empty:
                    max_score_row_for_star_athlete = event_data_for_plot.loc[event_data_for_plot['Score'].idxmax()]
                    fig_athlete.add_annotation(x=max_score_row_for_star_athlete['x_display'], y=max_score_row_for_star_athlete['Score'],
                                       text="⭐", showarrow=False, font=dict(size=STAR_ANNOTATION_FONT_SIZE))

                if current_y_axis_range_athlete:
                    fig_athlete.update_yaxes(range=current_y_axis_range_athlete)
                st.plotly_chart(fig_athlete, use_container_width=True)
            else:
                no_data_message_athlete = f"No data available for {event} at Level {selected_level}"
                if show_current_year_only and most_recent_comp_year_val is not None and pd.notna(most_recent_comp_year_val):
                     no_data_message_athlete += f" in {int(most_recent_comp_year_val)}."
                else:
                     no_data_message_athlete += "."
                st.write(no_data_message_athlete)

    # Multi-Year Comparison Logic
    if not show_current_year_only and not sub_level_data.empty:
        current_level_athlete = selected_level
        all_data_at_selected_level_athlete = sub_level_data.copy()

        all_comp_years_at_this_level_numeric_athlete = []
        if 'CompYear' in all_data_at_selected_level_athlete.columns:
            all_data_at_selected_level_athlete['CompYear_numeric'] = pd.to_numeric(all_data_at_selected_level_athlete['CompYear'], errors='coerce')
            all_data_at_selected_level_athlete.dropna(subset=['CompYear_numeric'], inplace=True)
            all_comp_years_at_this_level_numeric_athlete = sorted(all_data_at_selected_level_athlete.CompYear_numeric.unique())
        
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
                        
                        comparison_df_athlete['Event'] = pd.Categorical(comparison_df_athlete['Event'], categories=EVENTS_ORDER, ordered=True)
                        comparison_df_athlete = comparison_df_athlete.dropna(subset=['Event'])
                        comparison_df_athlete = comparison_df_athlete.sort_values('Event')

                        if 'All Around' in comparison_df_athlete['Event'].values:
                            aa_condition_athlete = comparison_df_athlete['Event'] == 'All Around'
                            comparison_df_athlete.loc[aa_condition_athlete, 'Score'] = comparison_df_athlete.loc[aa_condition_athlete, 'Score'] / 4
                        
                        fig_compare_athlete = px.bar(
                            comparison_df_athlete,
                            x="Event", y="Score", color="CompYear", barmode="group",
                            labels={"Score": "Score (AA / 4)", "Event": "Event", "CompYear": "Competition Year"},
                            text="Score",
                            category_orders={"CompYear": sorted_comp_years_for_chart_athlete}
                        )
                        fig_compare_athlete.update_traces(
                            **COMMON_BAR_TRACE_ARGS, 
                            texttemplate='%{text:.3f}',
                            textfont=dict(size=MARKER_TEXTFONT_SIZE)
                        )
                        fig_compare_athlete.update_layout(
                            **COMMON_LAYOUT_ARGS,
                            yaxis_title="Score (AA scores are divided by 4)",
                            yaxis_range=COMPARISON_BAR_Y_RANGE,
                            legend_title_text="Year",
                            height=500,
                            xaxis=dict(tickfont=dict(size=XAXIS_TICKFONT_SIZE)),
                            yaxis=dict(tickfont=dict(size=YAXIS_TICKFONT_SIZE))
                        )
                        st.plotly_chart(fig_compare_athlete, use_container_width=True)
                    else:
                        st.info(f"Not enough data (multiple years) for {selected_comparison_meet_athlete} at Level {current_level_athlete} to compare.")
            else:
                st.sidebar.info(f"No meets found in {primary_comp_year_for_meets_athlete} (most recent year at Level {current_level_athlete}) to enable comparison.")
        elif len(all_comp_years_at_this_level_numeric_athlete) == 1:
            st.sidebar.info(f"{athlete} has only competed at Level {current_level_athlete} in a single year ({int(all_comp_years_at_this_level_numeric_athlete[0])}). Multi-year meet comparison not available.")
        else:
            st.sidebar.info(f"{athlete} has no competition year data for Level {current_level_athlete}. Multi-year comparison not available.") 