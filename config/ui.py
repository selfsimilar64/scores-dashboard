from plotly.colors import sequential

# Color palettes
EVENT_COLORS = {
    "Vault": "blue",
    "Bars": "red",
    "Beam": "green",
    "Floor": "purple",
    "All Around": "orange"
}

# Define custom sort order for levels to ensure consistent color mapping if needed elsewhere
# Though for color mapping, the dict keys are sufficient.
LEVEL_ORDER = [str(i) for i in range(1, 11)] + ["XB", "XS", "XG", "XP", "XD"]

numbered_level_colors = sequential.Purp # Using Purp as in the original code for numbered levels
LEVEL_COLORS = {}
for i, level in enumerate([str(j) for j in range(1, 11)]):
    # Scale index to fit within the length of the Purp color sequence
    # The original code had `t = i/10.0` and `numbered_level_colors[int(t*len(numbered_level_colors))]`
    # which effectively maps 0-9 to indices of the color list.
    # If Purp has e.g. 10 colors, this maps 0 to Purp[0], 1 to Purp[1], ..., 9 to Purp[9]
    # For level "1" (i=0) -> Purp[0], for level "10" (i=9) -> Purp[len-1] (assuming len is 10)
    idx = min(i, len(numbered_level_colors) - 1) # Ensure index is within bounds
    LEVEL_COLORS[level] = numbered_level_colors[idx]

LEVEL_COLORS.update({
    "XB": "rgb(205, 127, 50)",   # Bronze
    "XS": "rgb(192, 192, 192)", # Silver
    "XG": "rgb(255, 215, 0)",   # Gold
    "XP": "rgb(229, 228, 226)", # Platinum
    "XD": "rgb(185, 242, 255)"  # Diamond-like (light blue)
})

DARK_CARD_CSS = """
/* Styles for metric cards when they are the content of an st.column */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    height: 100%; /* Make the wrapper take full column height */
    display: flex; /* Ensure the child (stVerticalBlock) can effectively use height: 100% */
}

div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) {
    background-color: #2E2E4A !important; /* Uses theme color, !important to override defaults */
    padding: 1.25rem; /* 20px */
    border-radius: 0.5rem; /* 8px */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1); /* Subtle shadow */
    height: 100%; /* Make the card itself take full height of its wrapper */
    width: 100%; /* Ensure it takes full width of the column content area */
    display: flex; /* Added to help manage internal content distribution */
    flex-direction: column; /* Stack content (metric, caption) vertically */
    /* justify-content: space-between; */ /* Optional: if you want to push caption to bottom */
}

/* Ensure st.metric within these cards has a transparent background */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric {
    background-color: transparent !important;
}

/* Ensure text color for label, value, and delta within st.metric respects the theme */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric label,
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric div[data-testid="stMetricValue"],
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric span { /* For delta */
    color: #FFFFFF !important;
}

/* Style for st.caption (rendered as markdown) within these cards */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) div[data-testid="stCaptionContainer"] p {
    color: #FFFFFF !important;
    opacity: 0.75; /* Slightly less prominent caption */
    font-size: 0.875rem; /* Smaller font for caption */
}
"""

# Font configuration (example, can be expanded)
FONT_FAMILY = "Roboto, sans-serif" # A common sans-serif font 