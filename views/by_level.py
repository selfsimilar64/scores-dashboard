import streamlit as st
import pandas as pd
import plotly.express as px
from data.loader import load_db
from utils.maths import custom_round
from config import (
    EVENT_COLORS,
    DEFAULT_Y_RANGE,
    NORMALIZED_Y_RANGE,
    COMMON_LAYOUT_ARGS,
    COMMON_LINE_TRACE_ARGS,
    EVENTS_ORDER,
    LEVEL_OPTIONS_PREFIX,
    MEET_VIEW_LEVEL_ORDER,
    CALC_METHODS,
    DEFAULT_CALC_METHOD_TEAM,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE,
    STAR_ANNOTATION_FONT_SIZE,
    TOP_SCORES_COUNT,
    CUSTOM_TAB_CSS
)

# Normalization Helper Function with logging for edge cases and branch choices
def _normalize_scores_helper(
    scores_df: pd.DataFrame,
    stats_info: pd.DataFrame | None,
    normalization_method: str,
    comp_year: int | None, 
    level_filter: str, 
    event_filter: str | None = None
) -> pd.DataFrame:
    import logging
    logger = logging.getLogger("by_level_normalization")
    # Streamlit users may want to see logs in the UI as well
    def log_and_caption(msg):
        logger.info(msg)
        st.caption(f"[NormLog] {msg}")

    if normalization_method == "None":
        log_and_caption("Normalization method is 'None'; returning original scores.")
        return scores_df.copy()
    if stats_info is None:
        log_and_caption("Stats info is None; cannot normalize. Returning original scores.")
        return scores_df.copy()
    if stats_info.empty:
        log_and_caption("Stats info is empty; cannot normalize. Returning original scores.")
        return scores_df.copy()
    if scores_df.empty:
        log_and_caption("Scores dataframe is empty; nothing to normalize.")
        return scores_df.copy()

    df_to_normalize = scores_df.copy()
    context_stats = stats_info.copy()

    # Ensure 'CompYear' is numeric in both dataframes before filtering or merging
    if 'CompYear' in df_to_normalize.columns:
        df_to_normalize['CompYear'] = pd.to_numeric(df_to_normalize['CompYear'], errors='coerce')
    else:
        log_and_caption("'CompYear' column missing in scores_df.")
    if 'CompYear' in context_stats.columns:
        context_stats['CompYear'] = pd.to_numeric(context_stats['CompYear'], errors='coerce')
    else:
        log_and_caption("'CompYear' column missing in stats_info.")

    # Filter by comp_year when provided
    if comp_year is not None:
        before = len(context_stats)
        context_stats.dropna(subset=['CompYear'], inplace=True)
        context_stats = context_stats[context_stats['CompYear'] == comp_year]
        after = len(context_stats)
        log_and_caption(f"Filtering stats_info for CompYear={comp_year}: {before} -> {after} rows.")

    # Filter by level unless selecting all levels
    if 'Level' in context_stats.columns:
        if level_filter != LEVEL_OPTIONS_PREFIX:
            before = len(context_stats)
            context_stats = context_stats[context_stats['Level'] == level_filter]
            after = len(context_stats)
            log_and_caption(f"Filtering stats_info for Level='{level_filter}': {before} -> {after} rows!")
        else:
            log_and_caption(f"Level filter is LEVEL_OPTIONS_PREFIX ('{LEVEL_OPTIONS_PREFIX}'); not filtering by level.")
    else:
        msg = "'Level' column not found in stats_info. Cannot filter by level for normalization."
        log_and_caption(msg)
        st.warning(msg)
        return df_to_normalize

    # Filter by event if provided
    if event_filter:
        if 'Event' in context_stats.columns:
            before = len(context_stats)
            context_stats = context_stats[context_stats['Event'] == event_filter]
            after = len(context_stats)
            log_and_caption(f"Filtering stats_info for Event='{event_filter}': {before} -> {after} rows.")
        else:
            msg = "'Event' column not found in stats_info. Cannot filter by event for normalization."
            log_and_caption(msg)
            st.warning(msg)
            return df_to_normalize

    if context_stats.empty:
        log_and_caption("Context stats is empty after filtering; cannot normalize. Returning original scores.")
        return df_to_normalize

    merge_keys = ['MeetName', 'CompYear', 'Level', 'Event']
    stat_cols_to_bring = merge_keys[:]
    if normalization_method == "Median":
        stat_cols_to_bring.extend(['Median', 'MedAbsDev'])
        log_and_caption("Using Median normalization; will require 'Median' and 'MedAbsDev' columns.")
    elif normalization_method == "Mean":
        stat_cols_to_bring.extend(['Mean', 'StdDev'])
        log_and_caption("Using Mean normalization; will require 'Mean' and 'StdDev' columns.")
    else:
        log_and_caption(f"Unknown normalization method '{normalization_method}'; returning original scores.")
        return df_to_normalize

    missing_stat_cols = [col for col in stat_cols_to_bring if col not in context_stats.columns]
    if any(missing_stat_cols):
        msg = f"Stats data missing cols for {normalization_method} norm: {missing_stat_cols}. Scores unnormalized."
        log_and_caption(msg)
        st.warning(msg)
        return df_to_normalize
    if normalization_method == "None" or stats_info is None or stats_info.empty:
        return scores_df.copy()
    if scores_df.empty:
        return scores_df.copy()

    df_to_normalize = scores_df.copy()
    context_stats = stats_info.copy()

    # Ensure 'CompYear' is numeric in both dataframes before filtering or merging
    if 'CompYear' in df_to_normalize.columns:
        df_to_normalize['CompYear'] = pd.to_numeric(df_to_normalize['CompYear'], errors='coerce')
    if 'CompYear' in context_stats.columns:
        context_stats['CompYear'] = pd.to_numeric(context_stats['CompYear'], errors='coerce')

    # Filter by comp_year when provided
    if comp_year is not None:
        context_stats.dropna(subset=['CompYear'], inplace=True)
        context_stats = context_stats[context_stats['CompYear'] == comp_year]

    # Filter by level unless selecting all levels
    if 'Level' in context_stats.columns:
        if level_filter != LEVEL_OPTIONS_PREFIX:
            context_stats = context_stats[context_stats['Level'] == level_filter]
    else:
        st.warning("'Level' column not found in stats_info. Cannot filter by level for normalization.")
        return df_to_normalize

    # Filter by event if provided
    if event_filter:
        if 'Event' in context_stats.columns:
            context_stats = context_stats[context_stats['Event'] == event_filter]
        else:
            st.warning("'Event' column not found in stats_info. Cannot filter by event for normalization.")
            return df_to_normalize

    if context_stats.empty:
        return df_to_normalize

    merge_keys = ['MeetName', 'CompYear', 'Level', 'Event']
    stat_cols_to_bring = merge_keys[:]
    if normalization_method == "Median":
        stat_cols_to_bring.extend(['Median', 'MedAbsDev'])
    elif normalization_method == "Mean":
        stat_cols_to_bring.extend(['Mean', 'StdDev'])

    missing_stat_cols = [col for col in stat_cols_to_bring if col not in context_stats.columns]
    if any(missing_stat_cols):
        st.warning(f"Stats data missing cols for {normalization_method} norm: {missing_stat_cols}. Scores unnormalized.")
        return df_to_normalize

    final_stats_for_merge = context_stats[list(set(stat_cols_to_bring))].drop_duplicates(subset=merge_keys)

    missing_score_cols = [key for key in merge_keys if key not in df_to_normalize.columns]
    if any(missing_score_cols):
        st.error(f"Scores data missing keys for merge: {missing_score_cols}. Cannot normalize.")
        return df_to_normalize

    merged_df = pd.merge(df_to_normalize, final_stats_for_merge, on=merge_keys, how='left')

    calculated_any_normalization = False
    if normalization_method == "Median":
        if 'Median' in merged_df.columns and 'MedAbsDev' in merged_df.columns:
            norm_mask = merged_df['Median'].notna() & merged_df['MedAbsDev'].notna()
            merged_df.loc[norm_mask, 'NormalizedScore'] = (
                merged_df.loc[norm_mask, 'Score'] - merged_df.loc[norm_mask, 'Median']
            ) / (merged_df.loc[norm_mask, 'MedAbsDev'] * 1.4826 + 1e-9)
            merged_df.loc[~norm_mask, 'NormalizedScore'] = merged_df.loc[~norm_mask, 'Score']
            if norm_mask.any():
                calculated_any_normalization = True
        else:
            st.warning("Median/MedAbsDev cols not found post-merge. Scores unnormalized.")
            return df_to_normalize
    elif normalization_method == "Mean":
        if 'Mean' in merged_df.columns and 'StdDev' in merged_df.columns:
            norm_mask = merged_df['Mean'].notna() & merged_df['StdDev'].notna()
            merged_df.loc[norm_mask, 'NormalizedScore'] = (
                merged_df.loc[norm_mask, 'Score'] - merged_df.loc[norm_mask, 'Mean']
            ) / (merged_df.loc[norm_mask, 'StdDev'] + 1e-9)
            merged_df.loc[~norm_mask, 'NormalizedScore'] = merged_df.loc[~norm_mask, 'Score']
            if norm_mask.any():
                calculated_any_normalization = True
        else:
            st.warning("Mean/StdDev cols not found post-merge. Scores unnormalized.")
            return df_to_normalize

    if calculated_any_normalization:
        merged_df['Score'] = merged_df['NormalizedScore']
    elif normalization_method != "None":
        st.caption(f"Norm. ({normalization_method}) selected, but no valid stats found. Original scores shown.")

    cols_to_drop = ['Median', 'MedAbsDev', 'Mean', 'StdDev', 'NormalizedScore']
    merged_df = merged_df.drop(columns=[col for col in cols_to_drop if col in merged_df.columns], errors='ignore')
    return merged_df

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


    fig = px.bar(placement_df, x='Place', y='Count', text='Count',
                 title=f"Placement Distribution for {title_level_display} - {selected_year}",
                 labels={'Place': 'Place', 'Count': 'Number of Times Achieved'})
    fig.update_layout(xaxis_tickvals=list(range(1, 11)), yaxis=dict(showticklabels=False, title=dict(text=None)), yaxis_dtick=1) # Ensure x-axis shows 1-10 and y-axis has integer ticks, hide y-axis labels/title
    fig.update_traces(texttemplate='%{text}', textposition='outside') # Display count labels on bars
    st.plotly_chart(fig, use_container_width=True)


def create_top_scores_table(df: pd.DataFrame, stats_df: pd.DataFrame | None, normalization_method: str, selected_level: str, selected_year: int):
    """Creates and displays a table of top scores for a given level and year (count defined by TOP_SCORES_COUNT)."""
    title_level_display = "All Levels" if selected_level == LEVEL_OPTIONS_PREFIX else f"Level {selected_level}"
    
    # Prepare data for the table: filter by year and potentially level
    if selected_level == LEVEL_OPTIONS_PREFIX: # "All Teams"
        data_for_table_initial = df[df.CompYear == selected_year].copy()
    else:
        data_for_table_initial = df[(df.Level == selected_level) & (df.CompYear == selected_year)].copy()

    # Exclude "All Around" scores BEFORE normalization, as stats might not exist for AA or it has different scale
    data_for_table_no_aa = data_for_table_initial[data_for_table_initial.Event != "All Around"]

    if data_for_table_no_aa.empty:
        st.caption(f"No scores data available for {title_level_display} in {selected_year} (excluding All Around) to display top scores.")
        return

    # Normalize scores for the table (event_filter=None because we want to normalize all events in the table based on their specific stats)
    # The _normalize_scores_helper needs CompYear, Level, and Event for each score to find its corresponding stat.
    # It will merge using ['MeetName', 'CompYear', 'Level', 'Event']
    normalized_data_for_table = _normalize_scores_helper(
        data_for_table_no_aa, 
        stats_df, 
        normalization_method,
        selected_year,
        selected_level, # Pass the overall level filter for the table
        event_filter=None # Normalize based on each row's event by merging
    )
    
    # Sort by score AFTER potential normalization
    top_scores = normalized_data_for_table.sort_values(by="Score", ascending=False).head(TOP_SCORES_COUNT)

    if top_scores.empty: # Should be redundant if data_for_table_no_aa was not empty, but good practice
        st.caption(f"No top scores data available for {title_level_display} in {selected_year} (excluding All Around) after processing.")
        return

    # Select and rename columns, excluding CompYear for Level view, adding Event
    table_data = top_scores[["AthleteName", "Level","MeetName", "Event", "Place", "Score"]].copy()
    table_data['Place'] = table_data['Place'].astype(str) # Keep as string after fetching
    try:
        table_data['Place'] = pd.to_numeric(table_data['Place'], errors='coerce').fillna(0).astype(int)
    except ValueError:
        pass 
    # Display score with 3 decimal places, or more if normalized scores are very small
    score_display_format = "{:.3f}" if normalization_method == "None" else "{:.1f}"
    table_data['Score'] = table_data['Score'].apply(lambda x: score_display_format.format(x) if pd.notna(x) else "N/A")


    st.subheader(f"Top {TOP_SCORES_COUNT} Scores for {title_level_display} - {selected_year} (Excl. AA{', Norm.' if normalization_method != 'None' else ''})")
    st.table(table_data.reset_index(drop=True))


def render_by_level_view(df: pd.DataFrame, stats_df: pd.DataFrame | None, normalization_method: str):
    st.sidebar.header("Level View Options") 
    st.markdown(CUSTOM_TAB_CSS, unsafe_allow_html=True)
    
    # Ensure 'Level' column exists and is not all NaN, then create options
    if 'Level' not in df.columns or df['Level'].isnull().all():
        st.error("The 'Level' column is missing or empty in the data. Cannot render 'By Level' view.")
        return
    
    # Add LEVEL_OPTIONS_PREFIX to unique levels following configured order
    unique_levels = [lvl for lvl in MEET_VIEW_LEVEL_ORDER if lvl in df.Level.unique()]
    other_levels = [lvl for lvl in sorted(df.Level.unique()) if pd.notna(lvl) and lvl not in unique_levels]
    unique_levels += other_levels
    level_options = [LEVEL_OPTIONS_PREFIX] + unique_levels

    # Determine stats calculation method based on normalization selection
    stats_method = normalization_method if normalization_method != "None" else "Median"
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", True, key="level_fit_y_axis")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_level_team = st.selectbox("Choose team (Level)", level_options, key="main_team_level_selector_lvl") # Changed key
    
    # Filter main dataframe by selected level (or not, if "All Levels")
    if selected_level_team == LEVEL_OPTIONS_PREFIX:
        team_data_for_level_view = df.copy() # Use all data if "All Levels"
        level_display_name = "All Levels"
    else:
        team_data_for_level_view = df[df.Level == selected_level_team].copy()
        level_display_name = f"Level {selected_level_team}"

    if team_data_for_level_view.empty:
        st.warning(f"No data available for {level_display_name}.")
        return

    available_years = sorted(team_data_for_level_view.CompYear.unique(), reverse=True)
    if not available_years:
        st.warning(f"No competition year data available for {level_display_name}.")
        return
    
    with col2:
        selected_year = st.selectbox("Choose CompYear", available_years, key="main_team_year_selector_lvl") # Changed key
    
    # Filter further by selected_year for all components in this view
    data_for_selected_year_level = team_data_for_level_view[team_data_for_level_view.CompYear == selected_year]

    if data_for_selected_year_level.empty:
        st.warning(f"No data available for {level_display_name} in {selected_year}.")
        # Allow to proceed, individual components will handle empty states or show selectors.
    
    # --- Display Placement Histogram (uses original 'df' but filtered) ---
    # Placement is not score dependent, so it uses the main 'df' passed to the view,
    # filtered by the UI selections for level and year.
    st.markdown("---") 
    # Create histogram from the main df, filtered by the current selections
    # df_for_hist is the global df filtered by selections
    # If selected_level_team is "All Levels", create_placement_histogram will use all levels for that year
    # If a specific level is chosen, it will use that level for that year
    create_placement_histogram(df, selected_level_team, selected_year) 

    # --- Display Top Scores Table ---
    st.markdown("---")
    # For top scores, use data_for_selected_year_level which is already filtered by year and level.
    # selected_level_team tells the function if it's "All Levels" or a specific one for title and internal logic.
    create_top_scores_table(data_for_selected_year_level, stats_df, normalization_method, selected_level_team, selected_year)

    st.markdown("---") 

    # Data for event tabs: already filtered by year and level by this point.
    # This data will be *further* filtered by event inside the loop.
    # Normalization will happen *inside* the loop, per event.
    year_level_event_data_base = data_for_selected_year_level.copy()

    if year_level_event_data_base.empty:
        st.warning(f"No event data available for {level_display_name} in {selected_year} to display in tabs.")
        # No return here, let the tabs render as empty if needed.
    
    y_axis_title = "Normalized Score" if normalization_method != "None" else "Score"
    event_tabs = st.tabs([f"{event}" for event in EVENTS_ORDER]) # Changed tab titles

    for i, event in enumerate(EVENTS_ORDER):
        with event_tabs[i]:
            # Filter for the current event
            event_data_for_tab = year_level_event_data_base[year_level_event_data_base.Event == event]
            
            # Exclude Regional meets from line plots in team view
            if 'MeetName' in event_data_for_tab.columns:
                event_data_for_tab = event_data_for_tab[~event_data_for_tab['MeetName'].str.contains("regional", case=False, na=False)]
            
            # Apply normalization FOR THIS SPECIFIC EVENT
            # Pass selected_level_team (which can be "All Levels") and the specific event
            normalized_event_data_for_tab = _normalize_scores_helper(
                event_data_for_tab,
                stats_df,
                normalization_method,
                selected_year,
                selected_level_team, # This is the overall level filter for the view
                event_filter=event # Crucially, filter stats for this specific event
            )

            if not normalized_event_data_for_tab.empty:
                # AGGREGATION LOGIC (Mean score per meet)
                # This aggregation happens AFTER normalization.
                # If selected_level_team is "All Levels", we group by MeetName only.
                # This means if multiple levels have scores for the same meet and event,
                # their (potentially normalized) scores are averaged together for that meet's point on the graph.
                # This might be complex if different levels have different normalization stats.
                # The current _normalize_scores_helper normalizes row by row based on its Level and Event.
                # So, if data for "All Levels" is passed, each row is normalized according to its own Level's stats.
                # Then, the aggregation below averages these individually-normalized scores.
                
                if selected_level_team == LEVEL_OPTIONS_PREFIX: # "All Levels"
                    if 'MeetDate' in normalized_event_data_for_tab.columns:
                        # Group by MeetName, average the (normalized) scores, take max MeetDate for sorting
                        avg_event_scores = normalized_event_data_for_tab.groupby("MeetName", as_index=False).agg(
                            Score=("Score", "mean"), MeetDate=("MeetDate", "max")
                        ).sort_values(by="MeetDate").drop(columns=["MeetDate"])
                    else: # Fallback if MeetDate is not available
                        avg_event_scores = normalized_event_data_for_tab.groupby("MeetName", as_index=False).Score.mean().sort_values(by="MeetName")
                else: # Specific Level selected
                    if 'MeetDate' not in normalized_event_data_for_tab.columns:
                        st.warning(f"MeetDate column is missing for Level {selected_level_team}, {event}. Chronological order of meets not guaranteed.")
                        avg_event_scores = normalized_event_data_for_tab.groupby("MeetName", as_index=False).Score.mean()
                    else:
                        # Group by MeetName and MeetDate, average scores, then sort by MeetDate
                        avg_event_scores = normalized_event_data_for_tab.groupby(
                            ["MeetName", "MeetDate"], as_index=False
                        ).Score.mean().sort_values(by="MeetDate")

                if not avg_event_scores.empty:
                    # METRIC CARDS (using aggregated, potentially normalized scores)
                    team_max_score_details = avg_event_scores.loc[avg_event_scores['Score'].idxmax()]
                    team_max_score_val = custom_round(team_max_score_details['Score'])
                    team_max_score_meet = team_max_score_details['MeetName']
                    
                    team_chosen_stat_val = None
                    team_chosen_stat_label = f"{stats_method} Team Score"
                    if stats_method == "Median":
                        team_chosen_stat_val = custom_round(avg_event_scores['Score'].median())
                    else:
                        team_chosen_stat_val = custom_round(avg_event_scores['Score'].mean())

                    # TREND CALCULATION (based on aggregated, potentially normalized scores)
                    team_trend_val = "N/A"
                    num_meets_for_trend = len(avg_event_scores)
                    if num_meets_for_trend >= 2:
                        team_scores_series = avg_event_scores['Score'].reset_index(drop=True)
                        half_idx = num_meets_for_trend // 2
                        first_period_scores = team_scores_series.iloc[:half_idx + (num_meets_for_trend % 2)]
                        second_period_scores = team_scores_series.iloc[half_idx:]
                        
                        if not (first_period_scores.empty or first_period_scores.isnull().all() or \
                               second_period_scores.empty or second_period_scores.isnull().all()):
                            stat_first_period = custom_round(first_period_scores.median() if stats_method == "Median" else first_period_scores.mean())
                            stat_second_period = custom_round(second_period_scores.median() if stats_method == "Median" else second_period_scores.mean())
                            if pd.notna(stat_first_period) and pd.notna(stat_second_period):
                                team_trend_val = f"{custom_round(stat_second_period - stat_first_period):+.3f}"
                    
                    team_stat_cols = st.columns(3)
                    with team_stat_cols[0]:
                        st.metric(label=f"Max Team Score ({event})", value=f"{team_max_score_val:.3f}" if pd.notna(team_max_score_val) else "N/A")
                        st.caption(f"Meet: {team_max_score_meet}")
                    with team_stat_cols[1]:
                        st.metric(label=team_chosen_stat_label, value=f"{team_chosen_stat_val:.3f}" if pd.notna(team_chosen_stat_val) else "N/A")
                        st.caption("Avg over meets")
                    with team_stat_cols[2]:
                        st.metric(label="Intra-Year Team Trend", value=str(team_trend_val), delta_color="off")
                        st.caption("Comparison of 1st/2nd half stats")
                    
                    # PLOTTING (using aggregated, potentially normalized scores)
                    # Determine Y-axis range based on event type and fit_y_axis toggle
                    if not fit_y_axis:
                        if normalization_method != "None":
                            yrange_config = NORMALIZED_Y_RANGE
                            current_y_axis_range = yrange_config.all_around if event == "All Around" else yrange_config.event
                        else:
                            yrange_config = DEFAULT_Y_RANGE
                            current_y_axis_range = yrange_config.all_around if event == "All Around" else yrange_config.event
                    else:
                        current_y_axis_range = None # Let Plotly auto-fit

                    fig = px.line(avg_event_scores, x="MeetName", y="Score", 
                                    markers=True,
                                    color_discrete_sequence=[EVENT_COLORS.get(event, "black")],
                                    text="Score") # Text on markers
                    
                    score_display_format = "{:.3f}" if normalization_method == "None" else "{:.1f}"
                    fig.update_traces(
                        **COMMON_LINE_TRACE_ARGS,
                        texttemplate=[score_display_format.format(s) if pd.notna(s) else "" for s in avg_event_scores['Score']],
                        textfont=dict(size=MARKER_TEXTFONT_SIZE)
                    )


                    plot_layout_options = COMMON_LAYOUT_ARGS.copy()
                    xaxis_cfg = plot_layout_options.get('xaxis', {}).copy()
                    xaxis_cfg['tickfont'] = {'size': XAXIS_TICKFONT_SIZE}
                    plot_layout_options['xaxis'] = xaxis_cfg

                    yaxis_cfg = plot_layout_options.get('yaxis', {}).copy()
                    yaxis_cfg['title'] = {'text': y_axis_title} # Set dynamic Y-axis title
                    yaxis_cfg['tickfont'] = {'size': YAXIS_TICKFONT_SIZE}
                    if current_y_axis_range:
                        yaxis_cfg['range'] = current_y_axis_range
                    plot_layout_options['yaxis'] = yaxis_cfg
                    
                    # Add title to the plot
                    plot_title = f"{level_display_name} - {event} Scores ({selected_year})"
                    if normalization_method != "None":
                        plot_title += f" - {normalization_method} Normalized"
                    plot_layout_options['title'] = plot_title

                    fig.update_layout(**plot_layout_options)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.caption(f"No aggregated score data to display for {event} for {level_display_name} in {selected_year} after normalization/aggregation.")
            else:
                st.caption(f"No score data available for {event} for {level_display_name} in {selected_year} to display in this tab.") 

    st.write("selected_year type:", type(selected_year))
    st.write("stats_df.CompYear dtype:", stats_df.CompYear.dtype) 