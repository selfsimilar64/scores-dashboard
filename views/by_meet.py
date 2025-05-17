import streamlit as st
import pandas as pd
import plotly.express as px
from utils.maths import custom_round
from config import (
    LEVEL_COLORS,
    DEFAULT_Y_RANGE,
    COMMON_LAYOUT_ARGS,
    COMMON_BAR_TRACE_ARGS,
    MEET_VIEW_LEVEL_ORDER,
    MEET_VIEW_EVENTS_TO_GRAPH,
    MEET_VIEW_TEAM_SCORE_Y_RANGE,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE
)

def render_by_meet_view(df: pd.DataFrame):
    st.sidebar.header("Meet View Options") # Added header for clarity

    col1_meet, col2_meet = st.columns(2)

    available_years_for_meets = sorted(df.CompYear.unique(), reverse=True)
    if not available_years_for_meets:
        st.warning("No competition year data available.")
        return
    
    with col1_meet:
        selected_comp_year = st.selectbox("Choose CompYear", available_years_for_meets, key="main_meet_comp_year_selector")

    if not selected_comp_year:
        st.info("Please select a competition year.") # Should not happen if available_years_for_meets is not empty
        return

    year_specific_df = df[df.CompYear == selected_comp_year]
    meet_names = sorted(year_specific_df.MeetName.unique())
    if not meet_names:
        st.warning(f"No meet data available for {selected_comp_year}.")
        return
    
    with col2_meet:
        selected_meet = st.selectbox("Choose Meet", meet_names, key="main_meet_selector")
    
    if not selected_meet:
        st.info("Please select a meet.") # Should not happen if meet_names is not empty
        return

    meet_data = year_specific_df[year_specific_df.MeetName == selected_meet].copy()
    if meet_data.empty:
        st.warning(f"No data available for the selected meet: {selected_meet} in {selected_comp_year}.")
        return

    if 'Level' in meet_data.columns:
        canonical_level_map = {lo.lower(): lo for lo in MEET_VIEW_LEVEL_ORDER}
        def normalize_level(level_val_input):
            if pd.isna(level_val_input):
                return level_val_input
            s_level_val = str(level_val_input).strip()
            return canonical_level_map.get(s_level_val.lower(), s_level_val)
        meet_data['Level'] = meet_data['Level'].apply(normalize_level)
        meet_data = meet_data[meet_data['Level'].isin(MEET_VIEW_LEVEL_ORDER)]

    for event_name in MEET_VIEW_EVENTS_TO_GRAPH:
        st.markdown(f"### {event_name} Scores")
        event_meet_data = meet_data[meet_data.Event == event_name]

        if event_meet_data.empty:
            st.write(f"No data for {event_name} at this meet.")
            st.markdown("---")
            continue

        avg_scores_by_level = event_meet_data.groupby("Level").Score.mean().reset_index()
        avg_scores_by_level['Level'] = pd.Categorical(avg_scores_by_level['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
        avg_scores_by_level = avg_scores_by_level.dropna(subset=['Level'])
        avg_scores_by_level = avg_scores_by_level.sort_values("Level")
        avg_scores_by_level = avg_scores_by_level[avg_scores_by_level['Score'].notna()]
        
        if avg_scores_by_level.empty:
            st.write(f"No aggregated data for {event_name} by level at this meet.")
            st.markdown("---")
            continue
            
        levels_with_data_event = avg_scores_by_level['Level'].unique().tolist()
        if not levels_with_data_event:
            st.write(f"No data with defined levels for {event_name} at this meet.")
            st.markdown("---")
            continue

        cols = st.columns(2)
        with cols[0]:
            max_avg_score_row = avg_scores_by_level.loc[avg_scores_by_level['Score'].idxmax()]
            max_avg_level_score_val = custom_round(max_avg_score_row['Score'])
            max_avg_level_name = max_avg_score_row['Level']
            st.metric(label=f"Max Avg. Level Score ({event_name})", value=f"{max_avg_level_score_val:.3f}",
                       help=f"Highest average score for a Level: {max_avg_level_name}")
            if max_avg_level_name in LEVEL_COLORS:
                 st.markdown(f"<span style='color:{LEVEL_COLORS[max_avg_level_name]};'>●</span> Level {max_avg_level_name}", unsafe_allow_html=True)
            else:
                 st.caption(f"Level: {max_avg_level_name}")

        with cols[1]:
            max_individual_score_details = event_meet_data.loc[event_meet_data['Score'].idxmax()]
            max_individual_score_val = custom_round(max_individual_score_details['Score'])
            max_individual_athlete = max_individual_score_details['AthleteName']
            max_individual_level = max_individual_score_details['Level']
            st.metric(label=f"Max Individual Score ({event_name})", value=f"{max_individual_score_val:.3f}",
                       help=f"Athlete: {max_individual_athlete} (Level {max_individual_level})")
            st.caption(f"Athlete: {max_individual_athlete} (Level {max_individual_level})")

        fig_meet_event = px.bar(avg_scores_by_level, x="Level", y="Score",
                                labels={"Score": "Average Score", "Level": "Level"},
                                text="Score",
                                color="Level",
                                color_discrete_map=LEVEL_COLORS)
        
        fig_meet_event.update_traces(
            **COMMON_BAR_TRACE_ARGS, 
            texttemplate='%{text:.3f}',
            textfont=dict(size=MARKER_TEXTFONT_SIZE)
        )
        current_layout_args = COMMON_LAYOUT_ARGS.copy()
        current_layout_args['xaxis'] = {'type': 'category', 'categoryorder':'array', 'categoryarray': levels_with_data_event, 'tickfont': dict(size=XAXIS_TICKFONT_SIZE)}
        current_layout_args['yaxis'] = {'tickfont': dict(size=YAXIS_TICKFONT_SIZE)}
        current_layout_args['yaxis_title'] = f"Average Score ({event_name})"
        current_layout_args['showlegend'] = True
        fig_meet_event.update_layout(**current_layout_args)
        
        y_range = DEFAULT_Y_RANGE.all_around if event_name == "All Around" else DEFAULT_Y_RANGE.event
        fig_meet_event.update_yaxes(range=y_range)

        st.plotly_chart(fig_meet_event, use_container_width=True)
        st.markdown("---")

    # Team Score Bar Graph
    st.markdown("### Team Scores (Average of Top 3 All Around Scores)")
    aa_meet_data = meet_data[meet_data.Event == "All Around"]
    team_scores_list = []

    if not aa_meet_data.empty:
        aa_meet_data['Level'] = pd.Categorical(aa_meet_data['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
        aa_meet_data = aa_meet_data.dropna(subset=['Level'])

        for level_val in MEET_VIEW_LEVEL_ORDER:
            level_aa_data = aa_meet_data[aa_meet_data.Level == level_val]
            if len(level_aa_data) >= 3:
                top_3_scores = level_aa_data.nlargest(3, 'Score')['Score']
                team_score_avg = top_3_scores.mean()
                if pd.notna(team_score_avg):
                    team_scores_list.append({'Level': level_val, 'TeamScore': team_score_avg})
        
        if team_scores_list:
            team_scores_df = pd.DataFrame(team_scores_list)
            team_scores_df['Level'] = pd.Categorical(team_scores_df['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
            team_scores_df = team_scores_df.sort_values("Level")
            team_scores_df = team_scores_df[team_scores_df['TeamScore'].notna()]
            levels_with_team_data = team_scores_df['Level'].unique().tolist()

            if levels_with_team_data:
                fig_team_score = px.bar(team_scores_df, x="Level", y="TeamScore",
                                        labels={"TeamScore": "Average Team Score (Top 3 AA)", "Level": "Team Level"},
                                        text="TeamScore",
                                        color="Level",
                                        color_discrete_map=LEVEL_COLORS)
                
                fig_team_score.update_traces(
                    **COMMON_BAR_TRACE_ARGS, 
                    texttemplate='%{text:.3f}',
                    textfont=dict(size=MARKER_TEXTFONT_SIZE)
                )
                team_score_layout_args = COMMON_LAYOUT_ARGS.copy()
                team_score_layout_args['xaxis'] = {'type': 'category', 'categoryorder':'array', 'categoryarray': levels_with_team_data, 'tickfont': dict(size=XAXIS_TICKFONT_SIZE)}
                team_score_layout_args['yaxis'] = {'tickfont': dict(size=YAXIS_TICKFONT_SIZE)}
                team_score_layout_args['yaxis_title'] = "Average Team Score"
                team_score_layout_args['yaxis_range'] = MEET_VIEW_TEAM_SCORE_Y_RANGE
                team_score_layout_args['showlegend'] = True
                fig_team_score.update_layout(**team_score_layout_args)
                st.plotly_chart(fig_team_score, use_container_width=True)
            else:
                st.write("Not enough data to display Team Scores for this meet after filtering.")
        else:
            st.write("Not enough data (fewer than 3 athletes in AA per level or scores are NaN) to calculate Team Scores for this meet.")
    else:
        st.write("No All Around data available for this meet to calculate Team Scores.") 