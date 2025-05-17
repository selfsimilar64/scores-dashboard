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
    STAR_ANNOTATION_FONT_SIZE
)

def render_by_level_view(df: pd.DataFrame):
    st.sidebar.header("Level View Options") # Added header for clarity
    level_options = [LEVEL_OPTIONS_PREFIX] + sorted(df.Level.unique())
    calc_method_team = st.sidebar.radio(
        "Calculation Method for Team Stats", 
        CALC_METHODS, 
        index=CALC_METHODS.index(DEFAULT_CALC_METHOD_TEAM), 
        key="calc_method_team"
    )
    
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
    
    year_team_data_for_level = team_data_for_level[team_data_for_level.CompYear == selected_year]

    if year_team_data_for_level.empty:
        st.warning(f"No data available for {level_display_name} in {selected_year}.")
        return

    event_tabs = st.tabs(EVENTS_ORDER)

    for i, event in enumerate(EVENTS_ORDER):
        with event_tabs[i]:
            event_data_for_team_year = year_team_data_for_level[year_team_data_for_level.Event == event]
            
            if not event_data_for_team_year.empty:
                if 'MeetDate' not in event_data_for_team_year.columns:
                    st.error("MeetDate column is missing, cannot guarantee chronological order for meets.")
                    avg_event_scores = event_data_for_team_year.groupby("MeetName", as_index=False).Score.mean()
                else:
                    avg_event_scores = event_data_for_team_year.groupby(["MeetName", "MeetDate"], as_index=False).Score.mean()
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
                                team_trend_val = f"{custom_round(calculated_team_trend):+.2f}"
                            else:
                                team_trend_val = "N/A"
                    
                    team_stat_cols = st.columns(3)
                    with team_stat_cols[0]:
                        st.metric(label="Max Team Score", value=f"{team_max_score_val:.2f}")
                        st.caption(f"Meet: {team_max_score_meet}")
                    with team_stat_cols[1]:
                        st.metric(label=team_chosen_stat_label, value=f"{team_chosen_stat_val:.2f}")
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
                        texttemplate='%{text:.2f}',
                        textfont=dict(size=MARKER_TEXTFONT_SIZE)
                    )

                    if not avg_event_scores.empty:
                        max_score_row = avg_event_scores.loc[avg_event_scores['Score'].idxmax()]
                        fig.add_annotation(x=max_score_row['MeetName'], y=max_score_row['Score'],
                                           text="⭐", showarrow=False, font=dict(size=STAR_ANNOTATION_FONT_SIZE))

                    if current_y_axis_range:
                        fig.update_yaxes(range=current_y_axis_range)
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write(f"No average score data available for {event} for {level_display_name} in {selected_year}.")
            else:
                st.write(f"No data available for {event} for {level_display_name} in {selected_year}.") 