import streamlit as st
import pandas as pd
import plotly.express as px
from utils.maths import custom_round
from config import (
    LEVEL_COLORS,
    DEFAULT_Y_RANGE,
    NORMALIZED_Y_RANGE,
    COMMON_LAYOUT_ARGS,
    COMMON_BAR_TRACE_ARGS,
    MEET_VIEW_LEVEL_ORDER,
    MEET_VIEW_EVENTS_TO_GRAPH,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE,
    CUSTOM_TAB_CSS
)

# Normalization Helper Function (Adapted for by_meet.py)
# Key change: level_filter can be "__ALL_LEVELS__" to not filter stats by a specific level,
# allowing row-by-row normalization based on the 'Level' column in scores_df during merge.
ALL_LEVELS_SENTINEL = "__ALL_LEVELS__"

def _normalize_scores_helper(
    scores_df: pd.DataFrame,
    stats_info: pd.DataFrame | None,
    normalization_method: str,
    comp_year: int | None, 
    level_filter: str, # Can be a specific level string or ALL_LEVELS_SENTINEL
    event_filter: str | None = None
) -> pd.DataFrame:
    if normalization_method == "None" or stats_info is None or stats_info.empty:
        return scores_df.copy()
    if scores_df.empty: return scores_df.copy()

    df_to_normalize = scores_df.copy()
    context_stats = stats_info.copy()

    if comp_year is not None:
        context_stats = context_stats[context_stats['CompYear'] == comp_year]
    
    # If level_filter is not the sentinel, filter stats by that specific level.
    # Otherwise, stats for all levels (for the given comp_year) are considered for merging.
    if level_filter != ALL_LEVELS_SENTINEL:
        context_stats = context_stats[context_stats['Level'] == level_filter]

    if event_filter: 
        context_stats = context_stats[context_stats['Event'] == event_filter]
    
    if context_stats.empty:
        return df_to_normalize # No relevant stats found, return original

    merge_keys = ['MeetName', 'CompYear', 'Level', 'Event']
    stat_cols_to_bring = merge_keys[:]
    if normalization_method == "Median": stat_cols_to_bring.extend(['Median', 'MedAbsDev'])
    elif normalization_method == "Mean": stat_cols_to_bring.extend(['Mean', 'StdDev'])
    
    missing_stat_cols = [col for col in stat_cols_to_bring if col not in context_stats.columns]
    if any(missing_stat_cols):
        st.warning(f"Stats missing {missing_stat_cols} for {normalization_method}. No normalization.")
        return df_to_normalize

    final_stats_for_merge = context_stats[list(set(stat_cols_to_bring))].drop_duplicates(subset=merge_keys)
    
    missing_score_cols = [key for key in merge_keys if key not in df_to_normalize.columns]
    if any(missing_score_cols):
        st.error(f"Scores missing {missing_score_cols} for merge. No normalization.")
        return df_to_normalize

    merged_df = pd.merge(df_to_normalize, final_stats_for_merge, on=merge_keys, how='left')
    calculated_any = False
    score_col_name = 'Score' # The column to normalize and update

    if normalization_method == "Median":
        if 'Median' in merged_df.columns and 'MedAbsDev' in merged_df.columns:
            mask = merged_df['Median'].notna() & merged_df['MedAbsDev'].notna() & (merged_df['MedAbsDev'] != 0)
            merged_df.loc[mask, 'NormalizedScore'] = (merged_df.loc[mask, score_col_name] - merged_df.loc[mask, 'Median']) / (merged_df.loc[mask, 'MedAbsDev'] * 1.4826 + 1e-9)
            merged_df.loc[~mask, 'NormalizedScore'] = merged_df.loc[~mask, score_col_name]
            if mask.any(): calculated_any = True
    elif normalization_method == "Mean":
        if 'Mean' in merged_df.columns and 'StdDev' in merged_df.columns:
            mask = merged_df['Mean'].notna() & merged_df['StdDev'].notna() & (merged_df['StdDev'] != 0)
            merged_df.loc[mask, 'NormalizedScore'] = (merged_df.loc[mask, score_col_name] - merged_df.loc[mask, 'Mean']) / (merged_df.loc[mask, 'StdDev'] + 1e-9)
            merged_df.loc[~mask, 'NormalizedScore'] = merged_df.loc[~mask, score_col_name]
            if mask.any(): calculated_any = True
    
    if calculated_any:
        merged_df[score_col_name] = merged_df['NormalizedScore']
    elif normalization_method != "None":
        st.caption(f"Norm. ({normalization_method}) selected, but no valid stats. Original scores shown.")

    cols_to_drop = ['Median', 'MedAbsDev', 'Mean', 'StdDev', 'NormalizedScore']
    merged_df = merged_df.drop(columns=[col for col in cols_to_drop if col in merged_df.columns], errors='ignore')
    return merged_df

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
                 labels={'Place': 'Place', 'Count': 'Number of Times Achieved'})
    fig.update_layout(xaxis_tickvals=list(range(1, 11)), yaxis=dict(showticklabels=False, title=dict(text=None)), yaxis_dtick=1)
    st.plotly_chart(fig, use_container_width=True)


def create_meet_top_scores_table(
    scores_df: pd.DataFrame, 
    stats_df: pd.DataFrame | None, 
    normalization_method: str, 
    selected_meet: str, 
    selected_year: int
):
    """Creates and displays a table of top 5 scores for a given meet and year."""
    data_for_table_initial = scores_df[(scores_df.MeetName == selected_meet) & (scores_df.CompYear == selected_year)].copy()
    data_for_table_no_aa = data_for_table_initial[data_for_table_initial.Event != "All Around"]

    if data_for_table_no_aa.empty:
        st.caption(f"No top scores (excl. AA) for {selected_meet} ({selected_year}).")
        return

    normalized_data_for_table = _normalize_scores_helper(
        data_for_table_no_aa,
        stats_df,
        normalization_method,
        selected_year, 
        level_filter=ALL_LEVELS_SENTINEL, # Normalize each score based on its own Level
        event_filter=None # Normalize each score based on its own Event
    )
    
    top_scores = normalized_data_for_table.sort_values(by="Score", ascending=False).head(5)

    if top_scores.empty:
        st.caption(f"No top scores after processing for {selected_meet} ({selected_year}).")
        return

    table_data = top_scores[["AthleteName", "Level", "Event", "Place", "Score"]].copy() # Added Level
    table_data['Place'] = table_data['Place'].astype(str)
    try: table_data['Place'] = pd.to_numeric(table_data['Place'], errors='coerce').fillna(0).astype(int)
    except ValueError: pass
    
    score_format = "{:.3f}" if normalization_method == "None" else "{:.4f}"
    table_data['Score'] = table_data['Score'].apply(lambda x: score_format.format(x) if pd.notna(x) else "N/A")

    norm_suffix = " (Normalized)" if normalization_method != 'None' else ""
    st.subheader(f"Top 5 Scores for {selected_meet} - {selected_year}{norm_suffix} (Excl. AA)")
    st.table(table_data.reset_index(drop=True))


def render_by_meet_view(df: pd.DataFrame, stats_df: pd.DataFrame | None, normalization_method: str):
    st.sidebar.header("Meet View Options")
    st.markdown(CUSTOM_TAB_CSS, unsafe_allow_html=True)
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", True, key="meet_fit_y_axis_meet") # Unique key

    col1_meet, col2_meet = st.columns(2)
    available_years = sorted(df.CompYear.unique(), reverse=True)
    if not available_years: st.warning("No CompYear data."); return
    
    with col1_meet: selected_comp_year = st.selectbox("CompYear", available_years, key="meet_year_selector")
    if not selected_comp_year: return

    year_df = df[df.CompYear == selected_comp_year]
    if 'MeetDate' in year_df.columns:
        year_df['MeetDate'] = pd.to_datetime(year_df['MeetDate'], errors='coerce')
        meets_list_df = year_df[['MeetName', 'MeetDate']].drop_duplicates().sort_values(by='MeetDate')
        states_m = meets_list_df[meets_list_df['MeetName'].str.contains("State", case=False, na=False)]
        other_m = meets_list_df[~meets_list_df['MeetName'].str.contains("State", case=False, na=False)]
        meet_names = pd.concat([other_m, states_m]).MeetName.unique().tolist()
    else: meet_names = sorted(year_df.MeetName.unique())

    if not meet_names: st.warning(f"No meets for {selected_comp_year}."); return
    with col2_meet: selected_meet = st.selectbox("Choose Meet", meet_names, key="meet_selector")
    if not selected_meet: return

    # meet_data_unnormalized is data for the specific meet and year, before any normalization
    meet_data_unnormalized = year_df[year_df.MeetName == selected_meet].copy()
    if meet_data_unnormalized.empty: st.warning(f"No data for {selected_meet} ({selected_comp_year})."); return

    st.markdown("---")
    create_meet_placement_histogram(df, selected_meet, selected_comp_year) # Uses main df for broader context if needed by its internal logic
    st.markdown("---")
    # Pass meet_data_unnormalized to top_scores, it will filter and then normalize
    create_meet_top_scores_table(meet_data_unnormalized, stats_df, normalization_method, selected_meet, selected_comp_year)
    st.markdown("---")

    # Normalize meet_data for all subsequent plots and calculations in tabs
    # This is done once for the selected meet and year, across all levels and events it contains.
    # The helper will normalize each row based on its specific Level and Event using stats for selected_comp_year.
    meet_data_for_tabs = _normalize_scores_helper(
        meet_data_unnormalized, 
        stats_df, 
        normalization_method, 
        selected_comp_year, 
        level_filter=ALL_LEVELS_SENTINEL, 
        event_filter=None # Normalize all events present
    )
    
    if 'Level' in meet_data_for_tabs.columns: # Standardize Level names after potential normalization
        canonical_level_map = {lo.lower(): lo for lo in MEET_VIEW_LEVEL_ORDER}
        meet_data_for_tabs['Level'] = meet_data_for_tabs['Level'].apply(lambda x: canonical_level_map.get(str(x).lower(), str(x)) if pd.notna(x) else x)
        meet_data_for_tabs = meet_data_for_tabs[meet_data_for_tabs['Level'].isin(MEET_VIEW_LEVEL_ORDER)]

    score_axis_label = "Normalized Score" if normalization_method != "None" else "Score"
    score_disp_format = "{:.3f}" if normalization_method == "None" else "{:.4f}"
    plot_title_norm_suffix = f" ({normalization_method} Norm)" if normalization_method != "None" else ""

    tab_labels = MEET_VIEW_EVENTS_TO_GRAPH + ["Team Scores"]
    event_tabs = st.tabs(tab_labels)

    # Event tabs (Bar charts)
    for i, event_name in enumerate(MEET_VIEW_EVENTS_TO_GRAPH):
        with event_tabs[i]:
            event_data_current_tab = meet_data_for_tabs[meet_data_for_tabs.Event == event_name]
            if event_data_current_tab.empty: st.write(f"No {event_name} data at this meet."); continue

            avg_scores_by_level = event_data_current_tab.groupby("Level").Score.mean().reset_index()
            avg_scores_by_level['Level'] = pd.Categorical(avg_scores_by_level['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
            avg_scores_by_level = avg_scores_by_level.dropna(subset=['Level', 'Score']).sort_values("Level")
            
            if avg_scores_by_level.empty: st.write(f"No aggregated {event_name} data by level."); continue
            levels_with_data = avg_scores_by_level['Level'].unique().tolist()

            # Metrics for event tab
            cols = st.columns(2)
            max_avg_score_row = avg_scores_by_level.loc[avg_scores_by_level['Score'].idxmax()]
            cols[0].metric(label=f"Max Avg Level Score ({event_name})", value=f"{custom_round(max_avg_score_row['Score']):.3f}", help=f"Level: {max_avg_score_row['Level']}")
            
            max_ind_score_details = event_data_current_tab.loc[event_data_current_tab['Score'].idxmax()]
            cols[1].metric(label=f"Max Indiv Score ({event_name})", value=f"{custom_round(max_ind_score_details['Score']):.3f}", help=f"Athlete: {max_ind_score_details['AthleteName']} (Lvl {max_ind_score_details['Level']})")

            # Bar chart for event tab
            fig = px.bar(avg_scores_by_level, x="Level", y="Score", text="Score", color="Level", color_discrete_map=LEVEL_COLORS)
            fig.update_traces(**COMMON_BAR_TRACE_ARGS, texttemplate=[score_disp_format.format(s) for s in avg_scores_by_level['Score']], textfont=dict(size=MARKER_TEXTFONT_SIZE))
            
            layout_args = COMMON_LAYOUT_ARGS.copy()
            layout_args['title'] = f"{selected_meet} - {event_name} Average Scores by Level{plot_title_norm_suffix}"
            layout_args['xaxis'] = {'type': 'category', 'categoryorder':'array', 'categoryarray': levels_with_data, 'tickfont': dict(size=XAXIS_TICKFONT_SIZE)}
            layout_args['yaxis'] = {'title': score_axis_label, 'tickfont': dict(size=YAXIS_TICKFONT_SIZE)}
            layout_args['showlegend'] = True # Show legend for Level colors
            fig.update_layout(**layout_args)

            y_event_range = DEFAULT_Y_RANGE.all_around if event_name == "All Around" else DEFAULT_Y_RANGE.event
            if not fit_y_axis: fig.update_yaxes(range=y_event_range)
            else: fig.update_yaxes(autorange=True)
            st.plotly_chart(fig, use_container_width=True)

    # Team Scores Tab
    with event_tabs[len(MEET_VIEW_EVENTS_TO_GRAPH)]:
        # Data for team scores is AA scores from the already meet-level normalized data.
        aa_event_data_for_team_calc = meet_data_for_tabs[meet_data_for_tabs.Event == "All Around"]
        
        st.markdown(f"### Team Scores (Avg of Top 3 All Around Scores){plot_title_norm_suffix}")
        team_scores_list = []
        if not aa_event_data_for_team_calc.empty:
            aa_event_data_for_team_calc['Level'] = pd.Categorical(aa_event_data_for_team_calc['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
            aa_event_data_for_team_calc = aa_event_data_for_team_calc.dropna(subset=['Level', 'Score'])

            for level_val in MEET_VIEW_LEVEL_ORDER:
                level_aa_data = aa_event_data_for_team_calc[aa_event_data_for_team_calc.Level == level_val]
                if len(level_aa_data) >= 3:
                    top_3 = level_aa_data.nlargest(3, 'Score')['Score']
                    if pd.notna(top_3.mean()): team_scores_list.append({'Level': level_val, 'TeamScore': top_3.mean()})
            
            if team_scores_list:
                team_scores_df = pd.DataFrame(team_scores_list)
                team_scores_df['Level'] = pd.Categorical(team_scores_df['Level'], categories=MEET_VIEW_LEVEL_ORDER, ordered=True)
                team_scores_df = team_scores_df.sort_values("Level")
                
                fig_team = px.bar(team_scores_df, x="Level", y="TeamScore", text="TeamScore", color="Level", color_discrete_map=LEVEL_COLORS)
                fig_team.update_traces(**COMMON_BAR_TRACE_ARGS, texttemplate=[score_disp_format.format(s) for s in team_scores_df['TeamScore']], textfont=dict(size=MARKER_TEXTFONT_SIZE))
                
                team_layout_args = COMMON_LAYOUT_ARGS.copy()
                team_layout_args['title'] = f"{selected_meet} - Team Scores by Level{plot_title_norm_suffix}"
                team_layout_args['xaxis'] = {'type': 'category', 'categoryorder':'array', 'categoryarray': MEET_VIEW_LEVEL_ORDER, 'tickfont': dict(size=XAXIS_TICKFONT_SIZE)}
                team_layout_args['yaxis'] = {'title': f"Team {score_axis_label}", 'tickfont': dict(size=YAXIS_TICKFONT_SIZE)}
                team_layout_args['showlegend'] = True
                fig_team.update_layout(**team_layout_args)
                
                if not fit_y_axis:
                    range_config = NORMALIZED_Y_RANGE.team_score if normalization_method != "None" else DEFAULT_Y_RANGE.team_score
                    fig_team.update_yaxes(range=range_config)
                else:
                    fig_team.update_yaxes(autorange=True)
                st.plotly_chart(fig_team, use_container_width=True)
            else:
                st.write("Not enough data to calculate team scores (need at least 3 AA scores per level).")
        else:
            st.write("No All Around data available for this meet to calculate team scores.") 