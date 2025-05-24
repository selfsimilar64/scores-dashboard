import streamlit as st
import pandas as pd
import plotly.express as px
from utils.maths import custom_round
from config import (
    EVENT_COLORS, 
    DEFAULT_Y_RANGE, 
    NORMALIZED_Y_RANGE,
    COMMON_LAYOUT_ARGS, 
    COMMON_LINE_TRACE_ARGS,
    # COMPARISON_BAR_Y_RANGE, # Assuming this might be for a different plot type not modified here
    COMMON_BAR_TRACE_ARGS, # Same as above
    EVENTS_ORDER,
    CALC_METHODS,
    DEFAULT_CALC_METHOD_ATHLETE,
    DEFAULT_SHOW_CURRENT_YEAR_ONLY,
    DEFAULT_FIT_Y_AXIS_ATHLETE,
    XAXIS_TICKFONT_SIZE,
    YAXIS_TICKFONT_SIZE,
    MARKER_TEXTFONT_SIZE,
    STAR_ANNOTATION_FONT_SIZE,
    TOP_SCORES_COUNT,
    CUSTOM_TAB_CSS
)
import logging
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
    selected_level: str, 
    show_current_year_only: bool, 
    most_recent_comp_year: int | None
):
    """Creates and displays a table of top 5 scores for a given gymnast, level, and year selection."""
    # Filter by athlete and level first
    data_for_table_initial = scores_df[(scores_df.AthleteName == selected_athlete) & (scores_df.Level == selected_level)].copy()

    title_year_segment = ""
    year_to_normalize = None # For _normalize_scores_helper

    if show_current_year_only and most_recent_comp_year is not None:
        data_for_table_initial = data_for_table_initial[data_for_table_initial.CompYear == most_recent_comp_year]
        title_year_segment = f" - {most_recent_comp_year}"
        year_to_normalize = most_recent_comp_year 
    elif show_current_year_only and most_recent_comp_year is None:
        st.caption(f"Top scores: Most recent year selected, but no CompYear found for {selected_athlete}, Level {selected_level}.")
        # data_for_table_initial remains all years for athlete/level; year_to_normalize remains None

    # Exclude "All Around" scores
    data_for_table_no_aa = data_for_table_initial[data_for_table_initial.Event != "All Around"]

    if data_for_table_no_aa.empty:
        st.caption(f"No top scores data (excl. AA) for {selected_athlete}, Level {selected_level}{title_year_segment}.")
        return

    # Normalize scores
    # If year_to_normalize is None, helper normalizes across all years present in data_for_table_no_aa based on matching CompYear in stats.
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
        st.caption(f"No top scores after processing for {selected_athlete}, Level {selected_level}{title_year_segment}.")
        return

    table_data = top_scores[["MeetName", "CompYear", "Event", "Place", "Score"]].copy()
    table_data['CompYear'] = table_data['CompYear'].astype(str)
    table_data['Place'] = table_data['Place'].astype(str)
    try:
        table_data['Place'] = pd.to_numeric(table_data['Place'], errors='coerce').fillna(0).astype(int)
    except ValueError:
        pass 
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
        st.warning(f"No levels found or selected for {athlete}. Please select a level or check data.")
        return # Exit if no level is determined/selected

    # Sidebar options
    show_current_year_only = False
    fit_y_axis = st.sidebar.checkbox("Fit Y-axis to data", DEFAULT_FIT_Y_AXIS_ATHLETE, key="gymnast_fit_y_axis_gym")
    
    # Filter data based on selected athlete AND level
    athlete_level_data = athlete_all_data[athlete_all_data.Level == selected_level].copy()
    if athlete_level_data.empty:
        st.warning(f"No data for {athlete} at Level {selected_level}.")
        return

    # Determine most_recent_comp_year_val based on athlete_level_data
    most_recent_comp_year_val = None
    if 'CompYear' in athlete_level_data.columns:
        numeric_comp_years = pd.to_numeric(athlete_level_data['CompYear'], errors='coerce')
        if numeric_comp_years.notna().any():
            most_recent_comp_year_val = int(numeric_comp_years.max())

    # Prepare base data for plots (potentially filtered by year)
    data_for_plots = athlete_level_data.copy()
    year_filter_for_norm_helper = None # For _normalize_scores_helper call

    if show_current_year_only:
        if most_recent_comp_year_val is not None:
            data_for_plots = data_for_plots[data_for_plots.CompYear == most_recent_comp_year_val]
            year_filter_for_norm_helper = most_recent_comp_year_val
        else:
            st.caption("'Show most recent CompYear' is selected, but no valid CompYear found for plots.")
            # data_for_plots remains all years for the selected athlete/level

    if 'MeetDate' not in data_for_plots.columns:
        st.error("MeetDate column missing. Cannot plot athlete data chronologically.")
        return       
    data_for_plots['MeetDate'] = pd.to_datetime(data_for_plots['MeetDate'], errors='coerce')
    data_for_plots.dropna(subset=['MeetDate'], inplace=True)
    data_for_plots = data_for_plots.sort_values(by="MeetDate") # Sort by MeetDate for chronological plots

    # Limit plots to two most recent years
    if 'CompYear' in data_for_plots.columns:
        comp_years_numeric = pd.to_numeric(data_for_plots['CompYear'], errors='coerce')
        recent_two_years = sorted(comp_years_numeric.dropna().unique(), reverse=True)[:2]
        data_for_plots = data_for_plots[comp_years_numeric.isin(recent_two_years)]

    if data_for_plots.empty:
        st.warning(f"No plottable data for {athlete} (Level {selected_level}) after date processing and year filtering.")
        # Display Top Scores table even if plot data is empty
        create_gymnast_top_scores_table(athlete_level_data, stats_df, normalization_method, athlete, selected_level, show_current_year_only, most_recent_comp_year_val)
        return
    
    # --- Display Top Scores Table ---
    st.markdown("---")
    # Pass athlete_level_data (data before year-filtering for plots, but after athlete/level selection)
    create_gymnast_top_scores_table(athlete_level_data, stats_df, normalization_method, athlete, selected_level, show_current_year_only, most_recent_comp_year_val)
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
                
                # Determine stats calculation method based on normalization selection
                stats_method = normalization_method if normalization_method != "None" else "Median"
                chosen_stat_val = custom_round(normalized_event_data['Score'].median() if stats_method == "Median" else normalized_event_data['Score'].mean())
                chosen_stat_label = f"{stats_method} Score"
                
                # Improvement calculation: difference between median values of current and previous year
                improvement_val_display = "N/A"
                improvement_label = "Year-over-Year Median Change"
                if 'CompYear' in normalized_event_data.columns:
                    normalized_event_data['CompYear'] = pd.to_numeric(normalized_event_data['CompYear'], errors='coerce')
                    unique_years = sorted(normalized_event_data['CompYear'].dropna().unique())
                    if len(unique_years) >= 2:
                        current_year = unique_years[-1]
                        previous_year = unique_years[-2]
                        current_median = custom_round(normalized_event_data[normalized_event_data['CompYear'] == current_year]['Score'].median())
                        previous_median = custom_round(normalized_event_data[normalized_event_data['CompYear'] == previous_year]['Score'].median())
                        diff = custom_round(current_median - previous_median)
                        improvement_val_display = f"{diff:+.3f}"
                    elif len(unique_years) == 1:
                        # Single-year data: compare first half vs second half including middle point
                        df_sorted = normalized_event_data.sort_values(by='MeetDate')
                        n = len(df_sorted)
                        mid = n // 2
                        first_half = df_sorted.iloc[:mid+1]
                        second_half = df_sorted.iloc[mid:]
                        stat_first = first_half['Score'].median() if stats_method == "Median" else first_half['Score'].mean()
                        stat_second = second_half['Score'].median() if stats_method == "Median" else second_half['Score'].mean()
                        diff_half = custom_round(stat_second - stat_first)
                        improvement_label = f"{stats_method} Half-Year Change"
                        improvement_val_display = f"{diff_half:+.3f}"
                
                stat_cols = st.columns(3)
                with stat_cols[0]: st.metric(label="Max Score", value=f"{max_score_val:.3f}" if pd.notna(max_score_val) else "N/A")
                with stat_cols[1]: st.metric(label=chosen_stat_label, value=f"{chosen_stat_val:.3f}" if pd.notna(chosen_stat_val) else "N/A")
                with stat_cols[2]: st.metric(label=improvement_label, value=improvement_val_display, delta_color="off")

                # --- PLOTTING --- (Based on normalized_event_data)
                # Determine if multiple years are actually present in the current event's data for plotting
                unique_comp_years_in_plot_data = []
                if 'CompYear' in normalized_event_data.columns:
                    # Ensure CompYear is treated as string for unique values and sorting, handling potential mixed types
                    normalized_event_data['CompYear'] = normalized_event_data['CompYear'].astype(str)
                    unique_comp_years_in_plot_data = sorted(normalized_event_data['CompYear'].unique(), key=lambda x: int(float(x)))

                plot_multiple_years = len(unique_comp_years_in_plot_data) > 1 and not show_current_year_only

                fig_title = f"{athlete} - {selected_level} - {event}{plot_title_norm_suffix}"
                if year_filter_for_norm_helper is not None: # This means show_current_year_only was true
                     fig_title += f" ({year_filter_for_norm_helper})"
                elif unique_comp_years_in_plot_data: # Only add year(s) if CompYear info exists
                    if len(unique_comp_years_in_plot_data) > 1 :
                        fig_title += f" (Years: {', '.join(unique_comp_years_in_plot_data)})"
                    elif len(unique_comp_years_in_plot_data) == 1:
                        fig_title += f" (Year: {unique_comp_years_in_plot_data[0]})"
                
                # Data for plotting, ensure it's sorted by CompYear then MeetDate to group meets by year sequentially
                current_plot_data = normalized_event_data.sort_values(by=['CompYear', 'MeetDate'])

                # Create composite x-axis label of Year - MeetName and order categories for x-axis
                current_plot_data['YearMeet'] = current_plot_data['CompYear'].astype(str) + ' - ' + current_plot_data['MeetName']
                chronological_yearmeets = current_plot_data['YearMeet'].unique().tolist()

                plot_params = {
                    "x": "YearMeet", "y": "Score",
                    "markers": True, "text": "Score",
                    "labels": {'Score': y_axis_title_plot},
                    "category_orders": {"YearMeet": chronological_yearmeets} # Base for all plots
                }

                if plot_multiple_years:
                    plot_params.update({
                        "color": "CompYear",
                        "line_group": "CompYear", # Ensures lines don't connect across years
                        "category_orders": {
                            "YearMeet": chronological_yearmeets,
                            "CompYear": unique_comp_years_in_plot_data # Sorted list of year strings
                        }
                    })
                else:
                    plot_params["color_discrete_sequence"] = [EVENT_COLORS.get(event, "black")]

                # Show trendline if desired
                show_trendline = st.checkbox("Show Trendline", key=f"trendline_{event}_{selected_level}_{athlete}")
                if show_trendline:
                    plot_params["trendline"] = "ols"
                    plot_params["trendline_scope"] = "overall"

                # Use scatter to enable trendline; draw lines and markers
                fig = px.scatter(current_plot_data, **plot_params)
                fig.update_traces(
                    mode='lines',
                    texttemplate='%{y:.3f}' if normalization_method == 'None' else '%{y:.1f}',
                    textposition='top center',
                    textfont=dict(size=MARKER_TEXTFONT_SIZE),
                    line=dict(width=COMMON_LINE_TRACE_ARGS['line']['width']),
                    marker=dict(size=COMMON_LINE_TRACE_ARGS['marker']['size'])
                )

                plot_layout = COMMON_LAYOUT_ARGS.copy()
                plot_layout['title'] = fig_title
                
                # Preserve original xaxis settings from COMMON_LAYOUT_ARGS, but ensure tickfont size is applied
                # COMMON_LAYOUT_ARGS already has 'showticklabels': False, 'title': {'text': None} for xaxis
                plot_layout['xaxis'] = {
                    **plot_layout.get('xaxis', {}), # Start with existing common settings for xaxis
                    'tickfont': {'size': XAXIS_TICKFONT_SIZE}
                }
                # Update yaxis title and tickfont size
                plot_layout['yaxis'] = {
                    **plot_layout.get('yaxis', {}), # Start with existing common settings for yaxis
                    'title': {'text': y_axis_title_plot}, 
                    'tickfont': {'size': YAXIS_TICKFONT_SIZE}
                }
                
                if not fit_y_axis:
                    if normalization_method != "None":
                        yrange_config = NORMALIZED_Y_RANGE 
                        plot_layout['yaxis']['range'] = yrange_config.all_around if event == "All Around" else yrange_config.event
                    else:
                        yrange_config = DEFAULT_Y_RANGE
                        plot_layout['yaxis']['range'] = yrange_config.all_around if event == "All Around" else yrange_config.event
                else:
                    # If yaxis range was set by COMMON_LAYOUT_ARGS, and we want to fit, remove it.
                    if 'range' in plot_layout['yaxis']:
                        plot_layout['yaxis'].pop('range')

                fig.update_layout(**plot_layout)
                # Highlight y=0 baseline when using normalized scores
                if normalization_method != 'None':
                    fig.add_hline(y=0, line=dict(color='white', width=5), layer='below')
                # Add star annotation on the highest score
                max_row_plot = current_plot_data.loc[current_plot_data['Score'].idxmax()]
                fig.add_trace(
                    px.scatter(
                        x=[max_row_plot['YearMeet']],
                        y=[max_row_plot['Score']],
                        text=[""],
                        opacity=1.0
                    ).update_traces(
                        marker_symbol="star",
                        marker_size=STAR_ANNOTATION_FONT_SIZE,
                        marker_color="gold",
                        showlegend=False,
                        hoverinfo="skip"
                    ).data[0]
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption(f"No {event} scores for {athlete} (Level {selected_level}) for the selected period.")

    # Multi-Year Comparison Logic
    if not show_current_year_only and not athlete_level_data.empty:
        current_level_athlete = selected_level
        all_data_at_selected_level_athlete = athlete_level_data.copy()

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
                            # yaxis_range=COMPARISON_BAR_Y_RANGE, # This was from config, ensuring it's used
                            legend_title_text="Year",
                            height=500, # from COMMON_LAYOUT_ARGS
                            # xaxis from COMMON_LAYOUT_ARGS has showticklabels=False, title=None. Override for this specific chart.
                            xaxis=dict(showticklabels=True, title=dict(text="Event"), tickfont=dict(size=XAXIS_TICKFONT_SIZE)),
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