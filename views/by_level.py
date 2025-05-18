import streamlit as st
import pandas as pd
import plotly.express as px
from data.loader import load_db
from utils.maths import custom_round
from config import (
    EVENT_COLORS,
    DEFAULT_Y_RANGE,
    COMMON_LAYOUT_ARGS,
    COMMON_LINE_TRACE_ARGS,
    EVENTS_ORDER,
    LEVEL_OPTIONS_PREFIX,
    CALC_METHODS,
    DEFAULT_CALC_METHOD_TEAM,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE,
    STAR_ANNOTATION_FONT_SIZE,
    CUSTOM_TAB_CSS
)

def create_placement_histogram(df: pd.DataFrame, selected_level: str, selected_year: int):
    """Creates and displays a histogram of placements for a given level and year."""
    title_level_display = "All Levels" if selected_level == LEVEL_OPTIONS_PREFIX else f"Level {selected_level}"
    if selected_level == LEVEL_OPTIONS_PREFIX: # "All Teams"
        data_for_histogram = df[df.CompYear == selected_year].copy()
    else:
        data_for_histogram = df[(df.Level == selected_level) & (df.CompYear == selected_year)].copy()

    if data_for_histogram.empty:
        st.caption(f"No placement data available for {title_level_display} in {selected_year}.")
        return

    # Filter for places 1-10 and ensure Place is integer
    data_for_histogram = data_for_histogram[data_for_histogram['Place'].isin(range(1, 11))]
    data_for_histogram['Place'] = data_for_histogram['Place'].astype(int)

    if data_for_histogram.empty:
        st.caption(f"No placements from 1 to 10 for {title_level_display} in {selected_year}.")
        return

    placement_counts = data_for_histogram['Place'].value_counts().sort_index()
    placement_df = pd.DataFrame({'Place': placement_counts.index, 'Count': placement_counts.values})

    # Ensure all places from 1 to 10 are present for the x-axis
    all_places = pd.DataFrame({'Place': range(1, 11)})
    placement_df = pd.merge(all_places, placement_df, on='Place', how='left').fillna(0)
    placement_df['Count'] = placement_df['Count'].astype(int) # Ensure count is integer for y-axis


    fig = px.bar(placement_df, x='Place', y='Count',
                 title=f"Placement Distribution for {title_level_display} - {selected_year}",
                 labels={'Place': 'Placement', 'Count': 'Number of Times Achieved'})
    fig.update_layout(xaxis_tickvals=list(range(1, 11)), yaxis_dtick=1) # Ensure x-axis shows 1-10 and y-axis has integer ticks
    st.plotly_chart(fig, use_container_width=True)


def create_top_scores_table(df: pd.DataFrame, selected_level: str, selected_year: int):
    """Creates and displays a table of top 5 scores for a given level and year."""
    title_level_display = "All Levels" if selected_level == LEVEL_OPTIONS_PREFIX else f"Level {selected_level}"
    if selected_level == LEVEL_OPTIONS_PREFIX: # "All Teams"
        data_for_table = df[df.CompYear == selected_year].copy()
    else:
        data_for_table = df[(df.Level == selected_level) & (df.CompYear == selected_year)].copy()

    # Exclude "All Around" scores and sort by score
    data_for_table = data_for_table[data_for_table.Event != "All Around"]
    top_scores = data_for_table.sort_values(by="Score", ascending=False).head(5)

    if top_scores.empty:
        st.caption(f"No top scores data available for {title_level_display} in {selected_year} (excluding All Around).")
        return

    # Select and rename columns, excluding CompYear for Level view
    table_data = top_scores[["AthleteName", "MeetName", "Placement", "Score"]].copy()
    table_data['Placement'] = table_data['Placement'].astype(str) # Keep as string after fetching
    # Attempt to convert to int, but allow non-integer (like 'N/A' or ties 'T1')
    try:
        table_data['Placement'] = pd.to_numeric(table_data['Placement'], errors='coerce').fillna(0).astype(int)
    except ValueError:
        pass # Keep as string if conversion fails
    table_data['Score'] = table_data['Score'].apply(lambda x: f"{x:.3f}")


    st.subheader(f"Top 5 Scores for {title_level_display} - {selected_year} (Excluding All Around)")
    st.table(table_data)


def render_by_level_view(df: pd.DataFrame):
    st.sidebar.header("Level View Options") # Added header for clarity
    st.markdown(CUSTOM_TAB_CSS, unsafe_allow_html=True) # Apply custom tab styles for tabs
    level_options = [LEVEL_OPTIONS_PREFIX] + sorted(df.Level.unique())
    calc_method_team = st.sidebar.radio(
        "Calculation Method for Team Stats", 
        CALC_METHODS, 
        index=CALC_METHODS.index(DEFAULT_CALC_METHOD_TEAM), 
        key="calc_method_team"
    )
    # Add Fit Y-axis toggle
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", True, key="level_fit_y_axis")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_level_team = st.selectbox("Choose team (Level)", level_options, key="main_team_level_selector")
    
    if selected_level_team == LEVEL_OPTIONS_PREFIX:
        team_data_for_level = df.copy()
        level_display_name = "All Teams"
    else:
        team_data_for_level = df[df.Level == selected_level_team]
        level_display_name = f"Level {selected_level_team}"

    if team_data_for_level.empty:
        st.warning(f"No data available for {level_display_name}.")
        return # Use return instead of st.stop()

    available_years = sorted(team_data_for_level.CompYear.unique(), reverse=True)
    if not available_years:
        st.warning(f"No competition year data available for {level_display_name}.")
        return
    
    with col2:
        selected_year = st.selectbox("Choose CompYear", available_years, key="main_team_year_selector")
    
    if df[(df.CompYear == selected_year) & 
            (df.Level if selected_level_team == LEVEL_OPTIONS_PREFIX else df.Level == selected_level_team)].empty:
        st.warning(f"No data available for {level_display_name} in {selected_year}.")
        # We might still want to show the selectors, so don't return immediately unless df is globally empty for year.
        # The individual components will handle their own empty states.

    # --- Display Placement Histogram ---
    st.markdown("---") # Visual separator
    create_placement_histogram(df, selected_level_team, selected_year)

    # --- Display Top Scores Table ---
    st.markdown("---") # Visual separator
    create_top_scores_table(df, selected_level_team, selected_year)

    st.markdown("---") # Visual separator before event tabs

    # Filter data for event tabs based on selected year and level
    year_team_data_for_level = team_data_for_level[team_data_for_level.CompYear == selected_year]
    if year_team_data_for_level.empty:
        # This check is specifically for the event tabs part
        st.warning(f"No event data available for {level_display_name} in {selected_year} to display in tabs.")
        # Optionally, do not proceed to render tabs if this specific filtered data is empty.
        # However, the histogram and top scores might still have data if selected_level_team is LEVEL_OPTIONS_PREFIX
        # and team_data_for_level had entries for the year but not for a specific level if one was chosen before this point.
        # For now, let's allow it to proceed, and the tab rendering logic will handle empty event_data_for_team_year.

    event_tabs = st.tabs(EVENTS_ORDER)

    for i, event in enumerate(EVENTS_ORDER):
        with event_tabs[i]:
            event_data_for_team_year = year_team_data_for_level[year_team_data_for_level.Event == event]
            
            if not event_data_for_team_year.empty:
                if selected_level_team == LEVEL_OPTIONS_PREFIX:
                    # All Teams: group by MeetName only, aggregate across dates, sorting by the latest date
                    if 'MeetDate' in event_data_for_team_year.columns:
                        avg_event_scores = event_data_for_team_year.groupby("MeetName", as_index=False).agg(
                            Score=("Score", "mean"), MeetDate=("MeetDate", "max")
                        )
                        avg_event_scores = avg_event_scores.sort_values(by="MeetDate")
                        avg_event_scores = avg_event_scores.drop(columns=["MeetDate"])
                    else:
                        avg_event_scores = event_data_for_team_year.groupby("MeetName", as_index=False).Score.mean()
                        avg_event_scores = avg_event_scores.sort_values(by="MeetName")
                else:
                    # Single Level: original grouping by MeetName & MeetDate for chronology
                    if 'MeetDate' not in event_data_for_team_year.columns:
                        st.error("MeetDate column is missing, cannot guarantee chronological order for meets.")
                        avg_event_scores = event_data_for_team_year.groupby("MeetName", as_index=False).Score.mean()
                    else:
                        avg_event_scores = event_data_for_team_year.groupby([
                            "MeetName", "MeetDate"
                        ], as_index=False).Score.mean()
                        avg_event_scores = avg_event_scores.sort_values(by="MeetDate")

                if not avg_event_scores.empty:
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
                        # Ensure indices are reset if they are not default, to avoid issues with iloc
                        team_scores_series = team_scores_series.reset_index(drop=True)

                        half_idx = num_meets_for_trend // 2
                        first_period_scores = team_scores_series.iloc[:half_idx + (num_meets_for_trend % 2)]
                        second_period_scores = team_scores_series.iloc[half_idx:]
                        
                        if first_period_scores.empty or first_period_scores.isnull().all() or \
                           second_period_scores.empty or second_period_scores.isnull().all():
                            team_trend_val = "N/A"
                        else:
                            stat_first_period = custom_round(first_period_scores.median() if calc_method_team == "Median" else first_period_scores.mean())
                            stat_second_period = custom_round(second_period_scores.median() if calc_method_team == "Median" else second_period_scores.mean())

                            if pd.notna(stat_first_period) and pd.notna(stat_second_period):
                                calculated_team_trend = stat_second_period - stat_first_period
                                team_trend_val = f"{custom_round(calculated_team_trend):+.3f}"
                            else:
                                team_trend_val = "N/A"
                    
                    team_stat_cols = st.columns(3)
                    with team_stat_cols[0]:
                        st.metric(label="Max Team Score", value=f"{team_max_score_val:.3f}")
                        st.caption(f"Meet: {team_max_score_meet}")
                    with team_stat_cols[1]:
                        st.metric(label=team_chosen_stat_label, value=f"{team_chosen_stat_val:.3f}")
                        st.caption("\u00A0")
                    with team_stat_cols[2]:
                        st.metric(label=team_trend_label, value=str(team_trend_val), delta_color="off")
                        st.caption("\u00A0")
                    
                    current_y_axis_range = DEFAULT_Y_RANGE.all_around if event == "All Around" else DEFAULT_Y_RANGE.event
                
                    fig = px.line(avg_event_scores, x="MeetName", y="Score", 
                                    markers=True,
                                    color_discrete_sequence=[EVENT_COLORS.get(event, "black")],
                                    text="Score")
                    
                    fig.update_layout(
                        **COMMON_LAYOUT_ARGS,
                        xaxis=dict(tickfont=dict(size=XAXIS_TICKFONT_SIZE)),
                        yaxis=dict(tickfont=dict(size=YAXIS_TICKFONT_SIZE))
                    )
                    fig.update_traces(
                        **COMMON_LINE_TRACE_ARGS, 
                        texttemplate='%{text:.3f}',
                        textfont=dict(size=MARKER_TEXTFONT_SIZE)
                    )

                    if not avg_event_scores.empty:
                        max_score_row = avg_event_scores.loc[avg_event_scores['Score'].idxmax()]
                        fig.add_annotation(x=max_score_row['MeetName'], y=max_score_row['Score'],
                                           text="⭐", showarrow=False, font=dict(size=STAR_ANNOTATION_FONT_SIZE))

                    if not fit_y_axis:
                        # only apply static y-range when toggle is off
                        fig.update_yaxes(range=current_y_axis_range)
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write(f"No data available for {event} for {level_display_name} in {selected_year}") 