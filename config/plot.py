from dataclasses import dataclass

@dataclass
class YAxisRange:
    event: tuple[float, float]
    all_around: tuple[float, float]
    team_score: tuple[float, float]

# Default Y-axis ranges, derived from common usage in app.py
DEFAULT_Y_RANGE = YAxisRange(
    event=(5.0, 10.0),
    all_around=(30.0, 40.0),
    team_score=(30.0, 40.0)
)

# Y-axis range for normalized scores (by median and by mean)
NORMALIZED_Y_RANGE = YAxisRange(
    event=(-3.0, 3.0),
    all_around=(-3.0, 3.0),  # Assuming AA also uses this range, adjust if needed
    team_score=(-3.0, 3.0)
)

# Y-axis range for the multi-year comparison bar chart in 'By Gymnast' view
# AA scores are divided by 4 for this chart, so max is 10.0, plus a bit of padding.
COMPARISON_BAR_Y_RANGE = (0.0, 10.5)

# Common layout settings for Plotly figures
# Extracted from various fig.update_layout calls in app.py
COMMON_LAYOUT_ARGS = dict(
    height=500,
    title_font_size=24,
    xaxis_title_font_size=22,
    yaxis_title_font_size=22,
    legend_title_font_size=22,
    legend_font_size=20,
    title_text="",  # Ensure title is blank by default, can be overridden
)

# New font size configurations
XAXIS_TICKFONT_SIZE = 18
YAXIS_TICKFONT_SIZE = 20
MARKER_TEXTFONT_SIZE = 18
STAR_ANNOTATION_FONT_SIZE = 25

# Specific trace updates for line charts
COMMON_LINE_TRACE_ARGS = dict(
    line=dict(width=8),
    marker=dict(size=18),
    textposition="top center"
    # texttemplate is often specific, e.g., '%{text:.2f}' or '%{text:.3f}'
)

# Specific trace updates for bar charts
COMMON_BAR_TRACE_ARGS = dict(
    marker=dict(line=dict(width=2, color='DarkSlateGrey')),
    textposition='outside'
    # texttemplate is often specific
) 