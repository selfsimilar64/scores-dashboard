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

DARK_CARD_CSS = """
/* Styles for metric cards when they are the content of an st.column */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    height: 100%; /* Make the wrapper take full column height */
    display: flex; /* Ensure the child (stVerticalBlock) can effectively use height: 100% */
}

div[data-testid="stColumn"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"]:has(.stMetric) {
    background-color: #2E2E4A !important; /* Uses theme color, !important to override defaults */
    padding: 1.25rem; /* 20px */
    border-radius: 1.5rem; /* 8px */
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
        color: #A0AEC0 !important; /* Light gray for inactive tab text */
        margin: 0 !important;
        line-height: 1.2 !important; /* Adjust for large font sizes */
        font-weight: 500 !important;
    }}

    /* Active tab button specific styling */
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: #36404F !important; /* Solid, contrasting background for active tab */
    }}

    /* Text within active tab button */
    button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p {{
        color: #FFFFFF !important; /* White text for active tab */
        font-weight: 600 !important; /* Bolder text for active tab */
    }}

    /* Optional: Hover effect for non-active tabs */
    button[data-baseweb="tab"]:not([aria-selected="true"]):hover {{
        background-color: #2A3038 !important; /* Slightly darker background on hover */
    }}
    button[data-baseweb="tab"]:not([aria-selected="true"]):hover div[data-testid="stMarkdownContainer"] p {{
        color: #E2E8F0 !important; /* Slightly lighter text on hover */
    }}

    /* Hide the default underline indicator */
    div[data-baseweb="tab-highlight"] {{
        display: none !important;
        height: 0px !important;
        color: transparent !important;
    }}

    /* Tab list container for spacing */
    div[data-baseweb="tab-list"] {{
        gap: 0.5rem !important; /* Space between tab buttons */
    }}
</style>
""" 