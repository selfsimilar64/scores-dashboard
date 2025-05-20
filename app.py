import streamlit as st
from data.loader import load_db
from config import DARK_CARD_CSS, VIEWS, DEFAULT_VIEW
from views import by_level, by_gymnast, by_meet

st.set_page_config(
    page_title="Gymnastics Scores Dashboard",
    page_icon="🤸",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'mailto:youremail@example.com',
        'Report a bug': "mailto:youremail@example.com",
        'About': "# Gymnastics Scores Dashboard\nThis app visualizes gymnastics competition scores."
    }
)

# Apply custom CSS for metric cards
st.markdown(f"""<style>{DARK_CARD_CSS}</style>""", unsafe_allow_html=True)

# Define normalization options
NORMALIZATION_OPTIONS = ["None", "Median", "Mean"]
DEFAULT_NORMALIZATION = "None"

# Ensure stats cards stay in a horizontal scroll container on mobile
st.markdown("""<style>
div[data-testid=\"stColumns\"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
}
div[data-testid=\"stColumns\"]::-webkit-scrollbar {
    display: none;
}
</style>""", unsafe_allow_html=True)

# Load data once
try:
    data = load_db() # Expect load_db to return a tuple or dict
    if isinstance(data, tuple) and len(data) == 2:
        df, stats_df = data
    else: # Fallback or handle error if load_db doesn't return two dfs
        st.error("Data loading did not return the expected format (scores_df, stats_df). Please check data/loader.py.")
        st.stop()

    if df is None or df.empty:
        st.error("Failed to load scores data or scores database is empty.")
        st.stop()
    if stats_df is None or stats_df.empty:
        st.warning("Stats data is not loaded or is empty. Normalization using Median/Mean might not work.")
        # We might not want to st.stop() if only stats_df is missing, as "None" normalization can still work.
except Exception as e:
    st.error(f"An error occurred during data loading: {e}")
    st.stop()

# --- Sidebar View Selector ---
st.sidebar.title("Dashboard Views")
view_selection = st.sidebar.radio(
    "Choose a view:",
    VIEWS,
    index=VIEWS.index(DEFAULT_VIEW) if DEFAULT_VIEW in VIEWS else 0,
    key="main_view_selector"
)

# --- Sidebar Normalization Selector ---
st.sidebar.title("Score Normalization")
normalization_selection = st.sidebar.radio(
    "Choose a normalization method:",
    NORMALIZATION_OPTIONS,
    index=NORMALIZATION_OPTIONS.index(DEFAULT_NORMALIZATION),
    key="normalization_selector"
)

# --- View Routing ---
def render_selected_view(selected_view, scores_data, statistics_data, normalization_method):
    if selected_view == "By Level":
        by_level.render_by_level_view(scores_data, statistics_data, normalization_method)
    elif selected_view == "By Gymnast":
        by_gymnast.render_by_gymnast_view(scores_data, statistics_data, normalization_method)
    elif selected_view == "By Meet":
        by_meet.render_by_meet_view(scores_data, statistics_data, normalization_method)
    else:
        st.error("Invalid view selected or view module not correctly loaded.")

render_selected_view(view_selection, df, stats_df, normalization_selection)
