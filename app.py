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

# Load data once
try:
    df = load_db()
    if df is None or df.empty: # load_db might return None or empty df on error
        st.error("Failed to load data or database is empty. Please check scores.db and data loader implementation.")
        st.stop() 
except Exception as e:
    st.error(f"An error occurred during data loading: {e}")
    st.stop()

# --- Sidebar View Selector ---
st.sidebar.title("Dashboard Views") # Add a title to the sidebar section
view_selection = st.sidebar.radio(
    "Choose a view:", 
    VIEWS, 
    index=VIEWS.index(DEFAULT_VIEW) if DEFAULT_VIEW in VIEWS else 0,
    key="main_view_selector"
)

# --- View Routing ---
def render_selected_view(selected_view, data_frame):
    if selected_view == "By Level":
        by_level.render_by_level_view(data_frame)
    elif selected_view == "By Gymnast":
        by_gymnast.render_by_gymnast_view(data_frame)
    elif selected_view == "By Meet":
        by_meet.render_by_meet_view(data_frame)
    else:
        st.error("Invalid view selected or view module not correctly loaded")

render_selected_view(view_selection, df)
