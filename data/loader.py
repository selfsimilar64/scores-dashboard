import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "database.db"
SCORES_TABLE_NAME = "scores" # Renamed for clarity
STATS_TABLE_NAME = "stats" # Added new table name

@st.cache_data
def load_db(path: str = DB_PATH) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Loads data from the SQLite database and returns a tuple of DataFrames (scores_df, stats_df)."""
    con = sqlite3.connect(path)
    scores_df = None
    stats_df = None
    try:
        # Load scores table
        try:
            scores_df = pd.read_sql(f"SELECT * FROM {SCORES_TABLE_NAME}", con)
        except pd.io.sql.DatabaseError as e:
            st.error(f"Could not load scores table '{SCORES_TABLE_NAME}': {e}. Please ensure the table exists and the schema is correct.")
            # Optionally, you could return (None, None) or raise the exception
            # depending on how critical this table is. For now, we'll allow proceeding
            # if only one table fails, as app.py has checks for None/empty dfs.

        # Load stats table
        try:
            stats_df = pd.read_sql(f"SELECT * FROM {STATS_TABLE_NAME}", con)
        except pd.io.sql.DatabaseError as e:
            # If stats table is missing, we can still run without normalization.
            # app.py will show a warning.
            st.warning(f"Could not load stats table '{STATS_TABLE_NAME}': {e}. Score normalization using Median/Mean will not be available.")
            stats_df = pd.DataFrame() # Return an empty DataFrame if stats table is not found or fails to load
            
    finally:
        con.close()
    return scores_df, stats_df

# Load the data globally for the app to use
# Any module importing this will have access to the dataframe `df`
# df = load_db()
# On second thought, it's better to call load_db() explicitly in app.py
# or where needed, to make data flow more explicit, especially with caching. 