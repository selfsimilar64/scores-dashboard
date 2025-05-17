import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "scores.db"
TABLE_NAME = "scores"

@st.cache_data
def load_db(path: str = DB_PATH) -> pd.DataFrame:
    """Loads data from the SQLite database and returns a DataFrame."""
    con = sqlite3.connect(path)
    try:
        df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", con)
    finally:
        con.close()
    return df

# Load the data globally for the app to use
# Any module importing this will have access to the dataframe `df`
# df = load_db()
# On second thought, it's better to call load_db() explicitly in app.py
# or where needed, to make data flow more explicit, especially with caching. 