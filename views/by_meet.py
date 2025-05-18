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
    MARKER_TEXTFONT_SIZE,
    CUSTOM_TAB_CSS
)

def create_meet_placement_histogram(df: pd.DataFrame, selected_meet: str, selected_year: int):
    """Creates and displays a histogram of placements for a given meet and year."""
    data_for_histogram = df[(df.MeetName == selected_meet) & (df.CompYear == selected_year)].copy()

    if data_for_histogram.empty:
        st.caption(f"No placement data available for {selected_meet} in {selected_year}.")
        return

    # Filter for places 1-10 and ensure Place is integer
    data_for_histogram = data_for_histogram[data_for_histogram['Place'].isin(range(1, 11))]
    data_for_histogram['Place'] = data_for_histogram['Place'].astype(int)

    if data_for_histogram.empty:
        st.caption(f"No placements from 1 to 10 for {selected_meet} in {selected_year}.")
        return

    placement_counts = data_for_histogram['Place'].value_counts().sort_index()
    placement_df = pd.DataFrame({'Place': placement_counts.index, 'Count': placement_counts.values})

    # Ensure all places from 1 to 10 are present for the x-axis
    all_places = pd.DataFrame({'Place': range(1, 11)})
    placement_df = pd.merge(all_places, placement_df, on='Place', how='left').fillna(0)
    placement_df['Count'] = placement_df['Count'].astype(int)


    fig = px.bar(placement_df, x='Place', y='Count',
                 title=f"Placement Distribution for {selected_meet} - {selected_year}",
                 labels={'Place': 'Placement', 'Count': 'Number of Times Achieved'})
    fig.update_layout(xaxis_tickvals=list(range(1, 11)), yaxis_dtick=1)
    st.plotly_chart(fig, use_container_width=True)


def create_meet_top_scores_table(df: pd.DataFrame, selected_meet: str, selected_year: int):
    """Creates and displays a table of top 5 scores for a given meet and year."""
    data_for_table = df[(df.MeetName == selected_meet) & (df.CompYear == selected_year)].copy()

    # Exclude "All Around" scores and sort by score
    data_for_table = data_for_table[data_for_table.Event != "All Around"]
    top_scores = data_for_table.sort_values(by="Score", ascending=False).head(5)

    if top_scores.empty:
        st.caption(f"No top scores data available for {selected_meet} in {selected_year} (excluding All Around).")
        return

    # Select and rename columns, omitting MeetName
    table_data = top_scores[["AthleteName", "CompYear", "Placement", "Score"]].copy()
    # CompYear is already selected, so it's redundant in the table for this view if only one year is processed.
    # However, the main df might contain multiple years, and this function receives `selected_year`.
    # For consistency with the request "CompYear column can be omitted for the Level view",
    # and "MeetName can be omitted for the Meet view", let's keep CompYear here.
    table_data['Placement'] = table_data['Placement'].astype(str)
    try:
        table_data['Placement'] = pd.to_numeric(table_data['Placement'], errors='coerce').fillna(0).astype(int)
    except ValueError:
        pass # Keep as string
    table_data['Score'] = table_data['Score'].apply(lambda x: f"{x:.3f}")


    st.subheader(f"Top 5 Scores for {selected_meet} - {selected_year} (Excluding All Around)")
    st.table(table_data)


def render_by_meet_view(df: pd.DataFrame):
    st.sidebar.header("Meet View Options") # Added header for clarity
    st.markdown(CUSTOM_TAB_CSS, unsafe_allow_html=True) # Apply custom tab styles

    # Add Fit Y-axis toggle
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", True, key="meet_fit_y_axis")

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

    # --- Display Placement Histogram ---
    st.markdown("---")
    create_meet_placement_histogram(df, selected_meet, selected_comp_year) # Pass the main df

    # --- Display Top Scores Table ---
    st.markdown("---")
    create_meet_top_scores_table(df, selected_meet, selected_comp_year) # Pass the main df

    st.markdown("---") # Separator before event tabs

    if 'Level' in meet_data.columns:
        canonical_level_map = {lo.lower(): lo for lo in MEET_VIEW_LEVEL_ORDER}
        def normalize_level(level_val_input):
            if pd.isna(level_val_input):
                return level_val_input
            s_level_val = str(level_val_input).strip()
            return canonical_level_map.get(s_level_val.lower(), s_level_val)
        meet_data['Level'] = meet_data['Level'].apply(normalize_level)
        meet_data = meet_data[meet_data['Level'].isin(MEET_VIEW_LEVEL_ORDER)]

    # Create tabs for each event and team scores
    tab_labels = MEET_VIEW_EVENTS_TO_GRAPH + ["Team Scores"]
    event_tabs = st.tabs(tab_labels)

    for i, event_name in enumerate(MEET_VIEW_EVENTS_TO_GRAPH):
        with event_tabs[i]:
            # st.markdown(f"### {event_name} Scores") # Title is now in the tab label
            event_meet_data = meet_data[meet_data.Event == event_name]

            if event_meet_data.empty:
                st.write(f"No data for {event_name} at this meet.")
                continue

            avg_scores_by_level = event_meet_data.groupby("Level").Score.mean().reset_index()
            avg_scores_by_level['Level'] = pd.Categorical(avg_scores_by_level['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
            avg_scores_by_level = avg_scores_by_level.dropna(subset=['Level'])
            avg_scores_by_level = avg_scores_by_level.sort_values("Level")
            avg_scores_by_level = avg_scores_by_level[avg_scores_by_level['Score'].notna()]
            
            if avg_scores_by_level.empty:
                st.write(f"No aggregated data for {event_name} by level at this meet.")
                continue
            
            levels_with_data_event = avg_scores_by_level['Level'].unique().tolist()
            if not levels_with_data_event:
                st.write(f"No data with defined levels for {event_name} at this meet.")
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
            # only apply static y-range when toggle is off
            if not fit_y_axis:
                fig_meet_event.update_yaxes(range=y_range)

            st.plotly_chart(fig_meet_event, use_container_width=True)

    # Team Scores Tab
    with event_tabs[len(MEET_VIEW_EVENTS_TO_GRAPH)]:
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
                    if not fit_y_axis:
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