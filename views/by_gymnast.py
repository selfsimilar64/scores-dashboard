import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.maths import custom_round
from config import (
    EVENT_COLORS, 
    DEFAULT_Y_RANGE, 
    NORMALIZED_Y_RANGE,
    COMMON_LAYOUT_ARGS, 
    COMMON_LINE_TRACE_ARGS,
    COMPARISON_BAR_Y_RANGE, # Assuming this might be for a different plot type not modified here
    COMMON_BAR_TRACE_ARGS, # Same as above
    EVENTS_ORDER,
    CALC_METHODS,
    DEFAULT_CALC_METHOD_ATHLETE,
    DEFAULT_FIT_Y_AXIS_ATHLETE,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE,
    STAR_ANNOTATION_FONT_SIZE,
    TOP_SCORES_COUNT,
    CUSTOM_TAB_CSS
)
import logging
# Add import for formatting helpers
from views.utils.formatting_helpers import format_place_emoji, format_meet_name_special, format_comp_year_emoji

logger = logging.getLogger()

# Normalization Helper Function (Copied and adjusted from by_level.py)
def _normalize_scores_helper(
    scores_df: pd.DataFrame,
    stats_info: pd.DataFrame | None,
    normalization_method: str,
    comp_year: int | None, # MODIFIED: Allow None for comp_year
    level_filter: str, # In gymnast view, this will always be a specific level
    event_filter: str | None = None
) -> pd.DataFrame:
    if normalization_method == "None" or stats_info is None or stats_info.empty:
        return scores_df.copy()

    if scores_df.empty:
        return scores_df.copy()

    df_to_normalize = scores_df.copy()
    context_stats = stats_info.copy() # Start with a copy of all stats_info

    # Ensure 'CompYear' is numeric in both dataframes before filtering or merging
    if 'CompYear' in df_to_normalize.columns:
        df_to_normalize['CompYear'] = pd.to_numeric(df_to_normalize['CompYear'], errors='coerce')
        # Optionally, convert to nullable Int64 if NaNs are acceptable and you want to keep them as integers
        # df_to_normalize['CompYear'] = df_to_normalize['CompYear'].astype('Int64')
    
    if 'CompYear' in context_stats.columns:
        context_stats['CompYear'] = pd.to_numeric(context_stats['CompYear'], errors='coerce')
        # context_stats['CompYear'] = context_stats['CompYear'].astype('Int64')

    # Now, CompYear in context_stats is numeric. Filter by comp_year (which is int | None)
    if comp_year is not None:
        # Drop NaNs from CompYear in context_stats if we are filtering by a specific year to avoid type issues with comparison if any NaNs remained
        context_stats.dropna(subset=['CompYear'], inplace=True)
        context_stats = context_stats[context_stats['CompYear'] == comp_year]

    # For gymnast view, level_filter is always a specific level string, not a prefix like LEVEL_OPTIONS_PREFIX
    if 'Level' in context_stats.columns:
        context_stats = context_stats[context_stats['Level'] == level_filter]
    else:
        logger.warning("'Level' column not found in stats_info. Cannot filter by level for normalization.")
        return df_to_normalize

    if event_filter:
        if 'Event' in context_stats.columns:
            context_stats = context_stats[context_stats['Event'] == event_filter]
        else:
            logger.warning("'Event' column not found in stats_info. Cannot filter by event for normalization.")
            return df_to_normalize
    
    if context_stats.empty:
        # st.caption(f"No relevant stats for normalization ({normalization_method}) for Lvl: {level_filter}, Yr: {comp_year}, Evt: {event_filter}.")
        return df_to_normalize

    merge_keys = ['MeetName', 'CompYear', 'Level', 'Event']
    stat_cols_to_bring = merge_keys[:]
    if normalization_method == "Median":
        stat_cols_to_bring.extend(['Median', 'MedAbsDev'])
    elif normalization_method == "Mean":
        stat_cols_to_bring.extend(['Mean', 'StdDev'])
    
    missing_stat_cols = [col for col in stat_cols_to_bring if col not in context_stats.columns]
    if any(missing_stat_cols):
        logger.warning(f"Stats data missing cols for {normalization_method} norm: {missing_stat_cols}. Scores unnormalized.")
        return df_to_normalize

    final_stats_for_merge = context_stats[list(set(stat_cols_to_bring))].drop_duplicates(subset=merge_keys)
    
    missing_score_cols = [key for key in merge_keys if key not in df_to_normalize.columns]
    if any(missing_score_cols):
        logger.error(f"Scores data missing keys for merge: {missing_score_cols}. Cannot normalize.")
        return df_to_normalize

    merged_df = pd.merge(df_to_normalize, final_stats_for_merge, on=merge_keys, how='left')

    calculated_any_normalization = False
    if normalization_method == "Median":
        if 'Median' in merged_df.columns and 'MedAbsDev' in merged_df.columns:
            norm_mask = merged_df['Median'].notna() & merged_df['MedAbsDev'].notna()
            merged_df.loc[norm_mask, 'NormalizedScore'] = (merged_df.loc[norm_mask, 'Score'] - merged_df.loc[norm_mask, 'Median']) / (merged_df.loc[norm_mask, 'MedAbsDev'] * 1.4826 + 1e-9)
            merged_df.loc[~norm_mask, 'NormalizedScore'] = merged_df.loc[~norm_mask, 'Score']
            if norm_mask.any(): calculated_any_normalization = True
        else:
            logger.warning("Median/MedAbsDev cols not found post-merge. Scores unnormalized.")
            return df_to_normalize
            
    elif normalization_method == "Mean":
        if 'Mean' in merged_df.columns and 'StdDev' in merged_df.columns:
            norm_mask = merged_df['Mean'].notna() & merged_df['StdDev'].notna()
            merged_df.loc[norm_mask, 'NormalizedScore'] = (merged_df.loc[norm_mask, 'Score'] - merged_df.loc[norm_mask, 'Mean']) / (merged_df.loc[norm_mask, 'StdDev'] + 1e-9)
            merged_df.loc[~norm_mask, 'NormalizedScore'] = merged_df.loc[~norm_mask, 'Score']
            if norm_mask.any(): calculated_any_normalization = True
        else:
            logger.warning("Mean/StdDev cols not found post-merge. Scores unnormalized.")
            return df_to_normalize
    
    if calculated_any_normalization:
        merged_df['Score'] = merged_df['NormalizedScore']
    elif normalization_method != "None":
        logger.info(f"Norm. ({normalization_method}) selected, but no valid stats found. Original scores shown.")

    cols_to_drop = ['Median', 'MedAbsDev', 'Mean', 'StdDev', 'NormalizedScore']
    merged_df = merged_df.drop(columns=[col for col in cols_to_drop if col in merged_df.columns], errors='ignore')
    return merged_df


def create_gymnast_top_scores_table(
    scores_df: pd.DataFrame, 
    stats_df: pd.DataFrame | None, 
    normalization_method: str, 
    selected_athlete: str, 
    selected_level: str
):
    """Creates and displays a table of top 5 scores for a given gymnast, level, and year selection."""
    # Filter by athlete and level first
    data_for_table_initial = scores_df[(scores_df.AthleteName == selected_athlete) & (scores_df.Level == selected_level)].copy()

    title_year_segment = "" # Will remain empty as year filtering is removed for table title
    year_to_normalize = None # Normalization will be based on all years in data_for_table_no_aa

    # Exclude "All Around" scores
    data_for_table_no_aa = data_for_table_initial[data_for_table_initial.Event != "All Around"]

    if data_for_table_no_aa.empty:
        st.caption(f"No top scores data (excl. AA) for {selected_athlete}, Level {selected_level}.")
        return

    # Normalize scores
    # year_to_normalize is None, so helper normalizes across all years present in data_for_table_no_aa.
    normalized_data_for_table = _normalize_scores_helper(
        data_for_table_no_aa,
        stats_df,
        normalization_method,
        year_to_normalize, # This can be an int or None
        selected_level,
        event_filter=None # Normalize all events based on their specific stats
    )
    
    top_scores = normalized_data_for_table.sort_values(by="Score", ascending=False).head(TOP_SCORES_COUNT)

    if top_scores.empty:
        st.caption(f"No top scores after processing for {selected_athlete}, Level {selected_level}.")
        return

    table_data = top_scores[["MeetName", "CompYear", "Event", "Place", "Score"]].copy()
    table_data['CompYear'] = table_data['CompYear'].astype(str)
    table_data['Place'] = table_data['Place'].astype(str)
    try:
        # Convert Place to numeric, coerce errors to NaN, then fill NaN with a placeholder (e.g., -1 or a string)
        # to distinguish from actual 0, before converting to int.
        table_data['Place_numeric'] = pd.to_numeric(table_data['Place'], errors='coerce')

        # Use the helper function for place formatting
        table_data['Place'] = table_data['Place_numeric'].apply(format_place_emoji)
        table_data = table_data.drop(columns=['Place_numeric'])

    except ValueError:
        # If conversion to numeric fails for all, keep original string or apply a default
        pass # Or table_data['Place'] = "" if all are problematic

    # MeetName formatting using helper
    table_data['MeetName'] = table_data['MeetName'].apply(format_meet_name_special)

    # CompYear formatting with colored circles using helper
    table_data['CompYear'] = format_comp_year_emoji(table_data['CompYear'])

    score_display_format = "{:.3f}" if normalization_method == "None" else "{:.4f}"
    table_data['Score'] = table_data['Score'].apply(lambda x: score_display_format.format(x) if pd.notna(x) else "N/A")

    norm_suffix = ", Norm." if normalization_method != 'None' else ''
    st.subheader(f"Top {TOP_SCORES_COUNT} Scores")
    st.table(table_data.reset_index(drop=True))


def render_by_gymnast_view(df: pd.DataFrame, stats_df: pd.DataFrame | None, normalization_method: str):
    st.sidebar.header("Gymnast View Options")
    st.markdown(CUSTOM_TAB_CSS, unsafe_allow_html=True)

    col1_gymnast, col2_gymnast = st.columns(2)
    with col1_gymnast:
        athlete_names = sorted(df.AthleteName.unique())
        if not athlete_names:
            st.warning("No athlete data available.")
            return
        athlete = st.selectbox("Choose athlete", athlete_names, key="main_athlete_selector_gym") # Unique key
    
    # Data for the selected athlete
    athlete_all_data = df[df.AthleteName == athlete]
    selected_level = None # Initialize

    if not athlete_all_data.empty:
        # Determine available levels for the athlete, sorted by recency of competition in that level
        if 'CompYear' in athlete_all_data.columns and 'Level' in athlete_all_data.columns:
            athlete_levels_years = athlete_all_data.groupby('Level')['CompYear'].max().reset_index()
            athlete_levels_years['CompYear'] = pd.to_numeric(athlete_levels_years['CompYear'], errors='coerce')
            athlete_levels_years = athlete_levels_years.sort_values(by='CompYear', ascending=False)
            athlete_levels_years.dropna(subset=['CompYear', 'Level'], inplace=True)
            sorted_levels = athlete_levels_years.Level.tolist()
        else:
            sorted_levels = sorted([lvl for lvl in athlete_all_data.Level.unique() if pd.notna(lvl)])

        if not sorted_levels:
            st.warning(f"No valid level data for athlete {athlete}.")
            # Don't return yet, allow UI to persist
        else:
            with col2_gymnast:
                selected_level = st.selectbox("Choose Level", sorted_levels, index=0, key="main_gymnast_level_selector_gym") # Unique key
    else:
        st.warning(f"No data available for athlete {athlete}.") 
        return # Exit if no data for selected athlete
    
    if selected_level is None: 
        # This case should ideally be rare if sorted_levels has content and a default is picked.
        # If sorted_levels was empty, the earlier warning about "No valid level data" would have appeared.
        st.warning(f"No level selected for {athlete}. Please select a level.")
        return # Exit if no level is determined/selected

    # Sidebar options
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", DEFAULT_FIT_Y_AXIS_ATHLETE, key="gymnast_fit_y_axis_gym")
    calc_method = st.sidebar.selectbox(
        "Statistics Calculation Method",
        CALC_METHODS,
        index=CALC_METHODS.index(DEFAULT_CALC_METHOD_ATHLETE) if DEFAULT_CALC_METHOD_ATHLETE in CALC_METHODS else 0,
        key="gymnast_calc_method",
        help="Choose method for calculating baseline statistics and metrics"
    )
    viz_type = st.sidebar.radio(
        "Visualization Type",
        ["Line Graph", "Dot Plot"],
        index=0,
        key="viz_type_gymnast",
        help="Line Graph: Connect points chronologically. Dot Plot: Show deviations from baseline (median/mean)."
    )
    
    # Filter data based on selected athlete AND level
    athlete_level_data = athlete_all_data[athlete_all_data.Level == selected_level].copy()
    if athlete_level_data.empty:
        st.warning(f"No data for {athlete} at Level {selected_level}.")
        return

    # Ensure CompYear is numeric for reliable processing, sorting, and filtering
    if 'CompYear' in athlete_level_data.columns:
        athlete_level_data['CompYear'] = pd.to_numeric(athlete_level_data['CompYear'], errors='coerce')
        # Optionally, decide if rows with NaN CompYear after conversion should be dropped
        # athlete_level_data.dropna(subset=['CompYear'], inplace=True) 
    
    all_comp_years_for_level = []
    if 'CompYear' in athlete_level_data.columns and athlete_level_data['CompYear'].notna().any():
        unique_years_numeric = athlete_level_data['CompYear'].dropna().unique()
        all_comp_years_for_level = sorted([int(y) for y in unique_years_numeric], reverse=True) # Desc order, e.g. [2024, 2023, 2022]

    # Prepare base data for plots, no longer filtered by a limited number of years here
    data_for_plots = athlete_level_data.copy()
    
    year_filter_for_norm_helper = None # Normalization in plot loop uses data as filtered above

    if 'MeetDate' not in data_for_plots.columns:
        st.error("MeetDate column missing. Cannot plot athlete data chronologically.")
        return       
    data_for_plots['MeetDate'] = pd.to_datetime(data_for_plots['MeetDate'], errors='coerce')
    data_for_plots.dropna(subset=['MeetDate'], inplace=True)
    data_for_plots = data_for_plots.sort_values(by="MeetDate") # Sort by MeetDate for chronological plots

    if data_for_plots.empty:
        st.warning(f"No plottable data for {athlete} (Level {selected_level}) after date processing and year filtering.")
        # Display Top Scores table even if plot data is empty
        # Call to create_gymnast_top_scores_table updated (removed show_current_year_only and most_recent_comp_year_val)
        create_gymnast_top_scores_table(athlete_level_data, stats_df, normalization_method, athlete, selected_level)
        return
    
    # --- Display Top Scores Table ---
    st.markdown("---")
    # Pass athlete_level_data (data before plot-specific year-filtering)
    # Call to create_gymnast_top_scores_table updated
    create_gymnast_top_scores_table(athlete_level_data, stats_df, normalization_method, athlete, selected_level)
    st.markdown("---")

    y_axis_title_plot = "Normalized Score" if normalization_method != "None" else "Score"
    score_display_format_plot = "{:.3f}" if normalization_method == "None" else "{:.4f}"
    plot_title_norm_suffix = f" ({normalization_method} Norm)" if normalization_method != "None" else ""

    event_tabs_gymnast = st.tabs([f"{event}" for event in EVENTS_ORDER])
    for i, event in enumerate(EVENTS_ORDER):
        with event_tabs_gymnast[i]:
            event_data_specific = data_for_plots[data_for_plots.Event == event].copy()
            
            # Normalize scores for THIS SPECIFIC EVENT and athlete/level context
            normalized_event_data = _normalize_scores_helper(
                event_data_specific,
                stats_df,
                normalization_method,
                year_filter_for_norm_helper, # This is most_recent_comp_year_val if show_current_year_only, else None
                selected_level,
                event_filter=event
            )

            if not normalized_event_data.empty:
                # --- METRICS --- (Based on normalized_event_data)
                max_score_details = normalized_event_data.loc[normalized_event_data['Score'].idxmax()]
                max_score_val = custom_round(max_score_details['Score'])
                
                # Use the selected calculation method for stats
                chosen_stat_val = custom_round(normalized_event_data['Score'].median() if calc_method == "Median" else normalized_event_data['Score'].mean())
                chosen_stat_label = f"{calc_method} Score"
                
                # Improvement calculation: difference between median/mean values of current and previous year
                improvement_val_display = "N/A"
                improvement_label = f"Year-over-Year {calc_method} Change"
                if 'CompYear' in normalized_event_data.columns:
                    normalized_event_data['CompYear'] = pd.to_numeric(normalized_event_data['CompYear'], errors='coerce')
                    unique_years = sorted(normalized_event_data['CompYear'].dropna().unique())
                    if len(unique_years) >= 2:
                        current_year = unique_years[-1]
                        previous_year = unique_years[-2]
                        current_stat = custom_round(normalized_event_data[normalized_event_data['CompYear'] == current_year]['Score'].median() if calc_method == "Median" else normalized_event_data[normalized_event_data['CompYear'] == current_year]['Score'].mean())
                        previous_stat = custom_round(normalized_event_data[normalized_event_data['CompYear'] == previous_year]['Score'].median() if calc_method == "Median" else normalized_event_data[normalized_event_data['CompYear'] == previous_year]['Score'].mean())
                        diff = custom_round(current_stat - previous_stat)
                        improvement_val_display = f"{diff:+.3f}"
                    elif len(unique_years) == 1:
                        # Single-year data: compare first half vs second half including middle point
                        df_sorted = normalized_event_data.sort_values(by='MeetDate')
                        n = len(df_sorted)
                        mid = n // 2
                        first_half = df_sorted.iloc[:mid+1]
                        second_half = df_sorted.iloc[mid:]
                        stat_first = first_half['Score'].median() if calc_method == "Median" else first_half['Score'].mean()
                        stat_second = second_half['Score'].median() if calc_method == "Median" else second_half['Score'].mean()
                        diff_half = custom_round(stat_second - stat_first)
                        improvement_label = f"{calc_method} Half-Year Change"
                        improvement_val_display = f"{diff_half:+.3f}"
                
                stat_cols = st.columns(3)
                with stat_cols[0]: st.metric(label="Max Score", value=f"{max_score_val:.3f}" if pd.notna(max_score_val) else "N/A")
                with stat_cols[1]: st.metric(label=chosen_stat_label, value=f"{chosen_stat_val:.3f}" if pd.notna(chosen_stat_val) else "N/A")
                with stat_cols[2]: st.metric(label=improvement_label, value=improvement_val_display, delta_color="off")

                # --- PLOTTING --- (Based on normalized_event_data)
                # Determine if multiple years are actually present in the current event's data for plotting
                unique_comp_years_in_plot_data = [] # This is a list of strings, sorted numerically ascending
                if 'CompYear' in normalized_event_data.columns:
                    numeric_years_in_plot = pd.to_numeric(normalized_event_data['CompYear'], errors='coerce').dropna().unique()
                    unique_comp_years_in_plot_data = sorted([str(int(y)) for y in numeric_years_in_plot], key=int)

                fig_title = ""
                if unique_comp_years_in_plot_data: 
                    if len(unique_comp_years_in_plot_data) > 1 :
                        fig_title += f" (Years: {', '.join(unique_comp_years_in_plot_data)})"
                    elif len(unique_comp_years_in_plot_data) == 1:
                        fig_title += f" (Year: {unique_comp_years_in_plot_data[0]})"
                
                current_plot_data = normalized_event_data.sort_values(by=['CompYear', 'MeetDate']).copy()

                if 'CompYear' in current_plot_data.columns:
                    current_plot_data['CompYear_str'] = current_plot_data['CompYear'].astype('Int64').astype(str).replace('<NA>', 'N/A')
                    current_plot_data['YearMeet'] = current_plot_data['CompYear_str'].replace('N/A', str(pd.NA)) + ' - ' + current_plot_data['MeetName']
                else:
                    current_plot_data['CompYear_str'] = "N/A"
                    current_plot_data['YearMeet'] = "N/A" + ' - ' + current_plot_data['MeetName']
                
                chronological_yearmeets = current_plot_data['YearMeet'].unique().tolist()
                YEAR_COLORS = ['#9A55FD', '#55a6fd', '#30cfcf', '#FF7F0E', '#2CA02C']
                
                sorted_unique_comp_years_for_plot_desc = sorted(unique_comp_years_in_plot_data, key=int, reverse=True)
                
                year_color_map = {
                    year_str: YEAR_COLORS[i % len(YEAR_COLORS)]
                    for i, year_str in enumerate(sorted_unique_comp_years_for_plot_desc)
                }

                fig = go.Figure()
                
                current_text_template = '%{y:.4f}' if normalization_method != "None" else '%{y:.3f}'

                if not current_plot_data.empty and sorted_unique_comp_years_for_plot_desc:
                    most_recent_year_str_for_plot = sorted_unique_comp_years_for_plot_desc[0]

                    # Calculate baselines for each year separately
                    year_baselines = {}
                    baseline_format = ".4f" if normalization_method != "None" else ".3f"
                    
                    for year_str in sorted_unique_comp_years_for_plot_desc:
                        year_data = current_plot_data[current_plot_data['CompYear_str'] == year_str]
                        if not year_data.empty:
                            year_baseline = year_data['Score'].median() if calc_method == "Median" else year_data['Score'].mean()
                            year_baselines[year_str] = year_baseline
                    
                    # Add horizontal baselines for each year (only spanning their data range)
                    for year_idx, (year_str, baseline_val) in enumerate(year_baselines.items()):
                        year_color = year_color_map.get(year_str, YEAR_COLORS[year_idx % len(YEAR_COLORS)])
                        year_meets = current_plot_data[current_plot_data['CompYear_str'] == year_str]['YearMeet'].unique()
                        
                        if len(year_meets) > 0:
                            # Only show baseline for first 2 years by default
                            is_visible_baseline = (year_idx < 2)
                            
                            if is_visible_baseline or len(sorted_unique_comp_years_for_plot_desc) <= 2:
                                # Get the leftmost and rightmost meets for this year
                                x_start = year_meets[0]  # First meet chronologically
                                x_end = year_meets[-1]   # Last meet chronologically
                                
                                fig.add_shape(
                                    type="line",
                                    x0=x_start, x1=x_end,
                                    y0=baseline_val, y1=baseline_val,
                                    line=dict(color=year_color, width=2, dash='dash'),
                                    layer='below'
                                )
                                

                    for year_idx, year_str_trace in enumerate(sorted_unique_comp_years_for_plot_desc):
                        trace_data = current_plot_data[current_plot_data['CompYear_str'] == year_str_trace]
                        if trace_data.empty:
                            continue

                        is_visible_trace = (year_idx < 2) # Show top 2 recent years by default
                        trace_color = year_color_map.get(year_str_trace, YEAR_COLORS[year_idx % len(YEAR_COLORS)])
                        
                        if viz_type == "Line Graph":
                            # Original line graph implementation
                            fig.add_trace(go.Scatter(
                                x=trace_data['YearMeet'],
                                y=trace_data['Score'],
                                mode='lines+markers+text',
                                name=f"{year_str_trace}",
                                line=dict(
                                    color=trace_color,
                                    width=COMMON_LINE_TRACE_ARGS['line']['width']
                                ),
                                marker=dict(
                                    color=trace_color,
                                    size=COMMON_LINE_TRACE_ARGS['marker']['size']
                                ),
                                text=trace_data['Score'],
                                texttemplate=current_text_template,
                                textposition='top center',
                                textfont=dict(size=MARKER_TEXTFONT_SIZE),
                                visible=True if is_visible_trace else 'legendonly',
                                legendgroup=year_str_trace,
                                showlegend=True,
                                customdata=trace_data[['MeetName', 'CompYear_str', 'Score']],
                                hovertemplate=
                                    "<b>Meet:</b> %{customdata[0]}<br>" +
                                    "<b>Year:</b> %{customdata[1]}<br>" +
                                    "<b>Score:</b> %{customdata[2]:" + ('.3f' if normalization_method == "None" else '.4f') + "}<extra></extra>"
                            ))
                        else:  # Dot Plot
                            year_baseline = year_baselines.get(year_str_trace, 0)  # Get year-specific baseline
                            
                            # Add scatter points
                            fig.add_trace(go.Scatter(
                                x=trace_data['YearMeet'],
                                y=trace_data['Score'],
                                mode='markers+text',
                                name=f"{year_str_trace}",
                                marker=dict(
                                    color=trace_color,
                                    size=COMMON_LINE_TRACE_ARGS['marker']['size'],  # Slightly larger for dot plot
                                    # line=dict(width=2, color='white')  # White border for better visibility
                                ),
                                text=[f"{score:{baseline_format}}" for score in trace_data['Score']],
                                textposition='top center',
                                textfont=dict(size=MARKER_TEXTFONT_SIZE),
                                visible=True if is_visible_trace else 'legendonly',
                                legendgroup=year_str_trace,
                                showlegend=True,
                                customdata=trace_data[['MeetName', 'CompYear_str', 'Score', 'Score']].apply(
                                    lambda row: [row[0], row[1], row[2], f"{row[2] - year_baseline:+{baseline_format}}"], axis=1
                                ).tolist(),
                                hovertemplate=
                                    "<b>Meet:</b> %{customdata[0]}<br>" +
                                    "<b>Year:</b> %{customdata[1]}<br>" +
                                    "<b>Score:</b> %{customdata[2]:" + ('.3f' if normalization_method == "None" else '.4f') + "}<br>" +
                                    "<b>Deviation:</b> %{customdata[3]}<extra></extra>"
                            ))
                            
                            # Add vertical connectors to year-specific baseline (only for visible traces)
                            if is_visible_trace:  # Add this condition
                                for idx, row in trace_data.iterrows():
                                    fig.add_shape(
                                        type="line",
                                        x0=row['YearMeet'], x1=row['YearMeet'],
                                        y0=year_baseline, y1=row['Score'],
                                        line=dict(
                                            color=trace_color,
                                            width=4,
                                            dash='solid'
                                        ),
                                        layer='below'
                                    )
                
                plot_layout = COMMON_LAYOUT_ARGS.copy()
                plot_layout['title'] = fig_title
                plot_layout['xaxis'] = {
                    **plot_layout.get('xaxis', {}),
                    'categoryorder': 'array',
                    'categoryarray': chronological_yearmeets,
                    'tickfont': {'size': XAXIS_TICKFONT_SIZE}
                }
                plot_layout['yaxis'] = {
                    **plot_layout.get('yaxis', {}),
                    'title': {'text': y_axis_title_plot}, 
                    'tickfont': {'size': YAXIS_TICKFONT_SIZE}
                }
                plot_layout['legend_title_text'] = "Year"
                plot_layout['legend'] = dict(traceorder='normal', itemsizing='constant')
                
                if not fit_y_axis:
                    if normalization_method != "None":
                        yrange_config = NORMALIZED_Y_RANGE 
                        plot_layout['yaxis']['range'] = yrange_config.all_around if event == "All Around" else yrange_config.event
                    else:
                        yrange_config = DEFAULT_Y_RANGE
                        plot_layout['yaxis']['range'] = yrange_config.all_around if event == "All Around" else yrange_config.event
                else: # fit_y_axis is True
                    if not current_plot_data.empty and 'Score' in current_plot_data.columns:
                        min_score = current_plot_data['Score'].min()
                        max_score = current_plot_data['Score'].max()
                        if pd.notna(min_score) and pd.notna(max_score):
                            plot_layout['yaxis']['range'] = [min_score - 0.75, max_score + 0.75]
                        else:
                            # Fallback to default auto-ranging if min/max score is NaN
                            if 'range' in plot_layout['yaxis']:
                                plot_layout['yaxis'].pop('range') 
                    else:
                        # Fallback to default auto-ranging if no data or Score column missing
                        if 'range' in plot_layout['yaxis']:
                            plot_layout['yaxis'].pop('range')

                fig.update_layout(**plot_layout)

                if normalization_method != 'None':
                    fig.add_hline(y=0, line=dict(color='white', width=5), layer='below')
                
                if not current_plot_data.empty: # Check if there's data to find a max score from
                    max_row_plot = current_plot_data.loc[current_plot_data['Score'].idxmax()]
                    fig.add_trace(
                        go.Scatter(
                            x=[max_row_plot['YearMeet']],
                            y=[max_row_plot['Score']],
                            mode='markers',
                            marker=dict(
                                symbol="star",
                                size=STAR_ANNOTATION_FONT_SIZE,
                                color="gold"
                            ),
                            name="Max Score",
                            showlegend=True,
                            hoverinfo="skip"
                        )
                    )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption(f"No {event} scores for {athlete} (Level {selected_level}) for the selected period.")

    # Multi-Year Comparison Logic
    # Removed 'not show_current_year_only' from the condition
    if not athlete_level_data.empty: # athlete_level_data has numeric CompYear if column exists
        current_level_athlete = selected_level
        # Use athlete_level_data which contains all years for this athlete/level for comparison purposes
        all_data_at_selected_level_athlete = athlete_level_data.copy() 

        all_comp_years_at_this_level_numeric_athlete = []
        if 'CompYear' in all_data_at_selected_level_athlete.columns and all_data_at_selected_level_athlete['CompYear'].notna().any():
            # CompYear is already numeric in all_data_at_selected_level_athlete
            all_comp_years_at_this_level_numeric_athlete = sorted(all_data_at_selected_level_athlete['CompYear'].dropna().unique())
            all_comp_years_at_this_level_numeric_athlete = [int(y) for y in all_comp_years_at_this_level_numeric_athlete]

        if len(all_comp_years_at_this_level_numeric_athlete) > 1:
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"Multi-Year Meet Comparison (Level {current_level_athlete})")

            primary_comp_year_for_meets_athlete = int(all_comp_years_at_this_level_numeric_athlete[-1])
            meets_in_primary_year_at_level_athlete = sorted(
                all_data_at_selected_level_athlete[
                    all_data_at_selected_level_athlete.CompYear == primary_comp_year_for_meets_athlete # Compare numeric CompYear
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
                        (all_data_at_selected_level_athlete.CompYear.isin(all_comp_years_at_this_level_numeric_athlete)) # Use numeric CompYear
                    ].copy()

                    if not comparison_df_athlete.empty and comparison_df_athlete.CompYear.nunique() > 1:
                        st.markdown("---")
                        st.header(f"Score Comparison: {selected_comparison_meet_athlete} (Level {current_level_athlete})")
                        
                        # Convert CompYear to string for display and categorical plotting here
                        comparison_df_athlete['CompYear_str'] = comparison_df_athlete['CompYear'].astype(int).astype(str)
                        sorted_comp_years_for_chart_athlete = sorted(comparison_df_athlete['CompYear_str'].unique(), key=int)
                        
                        st.subheader(f"Comparing Years: {', '.join(sorted_comp_years_for_chart_athlete)}")
                        
                        comparison_df_athlete['Event'] = pd.Categorical(comparison_df_athlete['Event'], categories=EVENTS_ORDER, ordered=True)
                        comparison_df_athlete = comparison_df_athlete.dropna(subset=['Event'])
                        comparison_df_athlete = comparison_df_athlete.sort_values('Event')

                        if 'All Around' in comparison_df_athlete['Event'].values:
                            aa_condition_athlete = comparison_df_athlete['Event'] == 'All Around'
                            comparison_df_athlete.loc[aa_condition_athlete, 'Score'] = comparison_df_athlete.loc[aa_condition_athlete, 'Score'] / 4
                        
                        fig_compare_athlete = px.bar(
                            comparison_df_athlete,
                            x="Event", y="Score", color="CompYear_str", barmode="group", # Use CompYear_str
                            labels={"Score": "Score (AA / 4)", "Event": "Event", "CompYear_str": "Competition Year"},
                            text="Score",
                            category_orders={"CompYear_str": sorted_comp_years_for_chart_athlete} # Use CompYear_str
                        )
                        fig_compare_athlete.update_traces(
                            **COMMON_BAR_TRACE_ARGS, 
                            texttemplate='%{text:.3f}',
                            textfont=dict(size=MARKER_TEXTFONT_SIZE)
                        )
                        fig_compare_athlete.update_layout(
                            **COMMON_LAYOUT_ARGS,
                            yaxis_title="Score (AA scores are divided by 4)",
                            # yaxis_range=COMPARISON_BAR_Y_RANGE, # This was from config, ensuring it's used
                            legend_title_text="Year",
                            # xaxis from COMMON_LAYOUT_ARGS has showticklabels=False, title=None. Override for this specific chart.
                            # xaxis=dict(showticklabels=True, title=dict(text="Event"), tickfont=dict(size=XAXIS_TICKFONT_SIZE)),
                            yaxis=dict(tickfont=dict(size=YAXIS_TICKFONT_SIZE), range=COMPARISON_BAR_Y_RANGE) # Explicitly use COMPARISON_BAR_Y_RANGE
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