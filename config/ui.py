from plotly.colors import sequential

# Theme Colors (from .streamlit/config.toml)
PRIMARY_COLOR = "#9A55FD"
BACKGROUND_COLOR = "#1d1d33"
SECONDARY_BACKGROUND_COLOR = "#2E2E4A"
TEXT_COLOR = "#ffffff"
TEXT_COLOR_SECONDARY = "#A0AEC0"

# Specific UI Element Colors (derived or specific choices)
INACTIVE_TEXT_COLOR = TEXT_COLOR_SECONDARY # Light gray for inactive tab text
TAB_HOVER_BG_COLOR = "#242440" # User-defined hover background for tabs
INACTIVE_HOVER_TEXT_COLOR = TEXT_COLOR_SECONDARY # Lighter text on hover for inactive tabs
ACTIVE_TAB_BG_COLOR = PRIMARY_COLOR

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
LEVEL_COLORS = {
    "3": "rgb(222, 218, 93)",
    "4": "rgb(119, 222, 93)",
    "5": "rgb(93, 222, 220)",
    "6": "rgb(93, 145, 222)",
    "7": "rgb(115, 93, 222)",
    "8": "rgb(190, 93, 222)",
    "9": "rgb(222, 93, 153)",
    "10": "rgb(222, 93, 93)"
}

LEVEL_COLORS.update({
    "XB": "rgb(205, 127, 50)",   # Bronze
    "XS": "rgb(192, 192, 192)", # Silver
    "XG": "rgb(255, 215, 0)",   # Gold
    "XP": "rgb(229, 228, 226)", # Platinum
    "XD": "rgb(185, 242, 255)"  # Diamond-like (light blue)
})

DARK_CARD_CSS = f"""
/* Styles for metric cards when they are the content of an st.column */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] {{
    height: 100%; /* Make the wrapper take full column height */
    display: flex; /* Ensure the child (stVerticalBlock) can effectively use height: 100% */
}}

div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) {{
    background-color: {SECONDARY_BACKGROUND_COLOR} !important; /* Uses theme color */
    padding: 1.25rem; /* 20px */
    border-radius: 1.5rem; /* 8px */
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1); /* Subtle shadow */
    height: 100%; /* Make the card itself take full height of its wrapper */
    width: 100%; /* Ensure it takes full width of the column content area */
    display: flex; /* Added to help manage internal content distribution */
    flex-direction: column; /* Stack content (metric, caption) vertically */
}}

/* Ensure st.metric within these cards has a transparent background */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric {{
    background-color: transparent !important;
}}

/* Ensure text color for label, value, and delta within st.metric respects the theme */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric label,
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric div[data-testid="stMetricValue"],
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) .stMetric span {{ /* For delta */
    color: {TEXT_COLOR} !important;
}}

/* Style for st.caption (rendered as markdown) within these cards */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) div[data-testid="stCaptionContainer"] p {{
    color: {TEXT_COLOR} !important;
    opacity: 0.75; /* Slightly less prominent caption */
    font-size: 0.875rem; /* Smaller font for caption */
}}
"""

# Font configuration (example, can be expanded)
FONT_FAMILY = "Roboto, sans-serif" # A common sans-serif font 

# Tab styling
TAB_FONT_SIZE = "2.0rem" # Default: 1rem. Increased for better readability

CUSTOM_TAB_CSS = f"""
<style>
    /* General tab button styling */
    button[data-baseweb="tab"] {{
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
        border: none !important;
        background-color: transparent !important;
        border-radius: 0.5rem !important; /* Rounded corners for all tabs */
        transition: background-color 0.2s ease-in-out;
    }}

    /* Text within all tab buttons */
    button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p {{
        font-size: {{TAB_FONT_SIZE}} !important;
        color: {INACTIVE_TEXT_COLOR} !important; /* Light gray for inactive tab text */
        margin: 0 !important;
        line-height: 1.2 !important; /* Adjust for large font sizes */
        font-weight: 500 !important;
    }}

    /* Active tab button specific styling */
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: {ACTIVE_TAB_BG_COLOR} !important; /* Solid, contrasting background for active tab */
    }}

    /* Text within active tab button */
    button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p {{
        color: {TEXT_COLOR} !important; /* White text for active tab */
        font-weight: 600 !important; /* Bolder text for active tab */
    }}

    /* Optional: Hover effect for non-active tabs */
    button[data-baseweb="tab"]:not([aria-selected="true"]):hover {{
        background-color: {TAB_HOVER_BG_COLOR} !important; /* Slightly darker background on hover */
    }}
    button[data-baseweb="tab"]:not([aria-selected="true"]):hover div[data-testid="stMarkdownContainer"] p {{
        color: {INACTIVE_HOVER_TEXT_COLOR} !important; /* Slightly lighter text on hover */
    }}

    /* Hide the default underline indicator */
    div[data-baseweb="tab-highlight"] {{
        height: 0px !important;
        color: {BACKGROUND_COLOR} !important;
    }}

    /* Tab list container for spacing */
    div[data-baseweb="tab-list"] {{
        gap: 0.5rem !important; /* Space between tab buttons */
    }}

    /* Hide or style the main tab border element */
    div[data-baseweb="tab-border"] {{
        display: none !important; /* Hide it */
        Alternatively, to make it blend if hiding is not desired:
        background-color: {BACKGROUND_COLOR} !important;
        border-color: {BACKGROUND_COLOR} !important;
        height: 1px !important; /* Or whatever height it has */
        
    }}
</style>
""" 