# Defines default behaviours and static choice lists for the application

# --- View Configuration ---
VIEWS = ["By Level", "By Gymnast", "By Meet"]
DEFAULT_VIEW = "By Level"

# --- Calculation Methods ---
CALC_METHODS = ["Median", "Mean"]
DEFAULT_CALC_METHOD_TEAM = "Median"
DEFAULT_CALC_METHOD_ATHLETE = "Median"

# --- Rounding ---
# The custom_round function in app.py rounds to the nearest 0.05 (1/20).
ROUNDING_STEP = 0.05

# --- Events ---
# Standard list of events, used for ordering tabs and other displays
EVENTS_ORDER = ["Vault", "Bars", "Beam", "Floor", "All Around"]

# --- "By Level" View specific ---
LEVEL_OPTIONS_PREFIX = "All teams" # The string used for the 'select all levels' option

# --- "By Gymnast" View specific ---
DEFAULT_SHOW_CURRENT_YEAR_ONLY = False
DEFAULT_FIT_Y_AXIS_ATHLETE = False

# --- "By Meet" View specific ---
# Level order for sorting and display in the 'By Meet' view
# This is also used for color mapping consistency if ui.LEVEL_ORDER is not sufficient
MEET_VIEW_LEVEL_ORDER = [str(i) for i in range(1, 11)] + ["XB", "XS", "XG", "XP", "XD"]
# Events to graph in the 'By Meet' view
MEET_VIEW_EVENTS_TO_GRAPH = ["Vault", "Bars", "Beam", "Floor", "All Around"]
# Y-axis range for team scores in 'By Meet' view (top 3 AA average)
MEET_VIEW_TEAM_SCORE_Y_RANGE = (30.0, 40.0) 