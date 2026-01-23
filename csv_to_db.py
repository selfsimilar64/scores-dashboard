import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_database_uri():
    """Get database URI from environment variable or default to local SQLite."""
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # SQLAlchemy requires postgresql:// not postgres://
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    return 'sqlite:///database.db'

def create_db_from_csv(csv_file_path: str, db_uri: str = None, table_name: str = 'scores'):
    """
    Reads a CSV file and creates/replaces a table in the specified database
    with the structure and data from the CSV.
    Data types are inferred by pandas.
    
    If db_uri is not provided, uses DATABASE_URL environment variable.
    """
    if db_uri is None:
        db_uri = get_database_uri()
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file_path)
        if df.empty and not pd.read_csv(csv_file_path, nrows=0).columns.tolist(): # Check if truly empty (no columns, no data)
            print(f"Error: The file '{csv_file_path}' is completely empty (no columns, no data).")
            return
        if df.empty: # Has columns, but no data
             print(f"Info: The file '{csv_file_path}' has headers but no data rows. An empty table '{table_name}' will be created.")


        # Create SQLite engine and write to database
        engine = create_engine(db_uri, echo=False)
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        
        db_file_name = db_uri.split("///")[-1] if "///" in db_uri else db_uri
        num_rows = len(df)
        if num_rows > 0:
            print(f"Successfully created table '{table_name}' in database '{db_file_name}' from '{csv_file_path}' with {num_rows} rows.")
        else:
            print(f"Successfully created an empty table '{table_name}' in database '{db_file_name}' from '{csv_file_path}' (CSV had headers but no data).")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
    except pd.errors.EmptyDataError: # Should be caught by initial checks, but as a fallback.
        print(f"Error: The file '{csv_file_path}' is empty or contains no data rows.")
    except Exception as e:
        print(f"An error occurred while creating table from '{csv_file_path}': {e}")

def append_data_from_csv(csv_file_path: str, db_uri: str = None, table_name: str = 'scores', chunk_size: int = 1000):
    """
    Reads data from a CSV file in chunks and appends it to the specified table in a database.
    This function assumes the table structure is compatible with the CSV data.
    No specific data transformations are applied to columns.

    Args:
        csv_file_path (str): The path to the CSV file.
        db_uri (str): The database URI. If not provided, uses DATABASE_URL environment variable.
        table_name (str): The name of the table to append to.
        chunk_size (int, optional): Number of rows per chunk to read from CSV. Defaults to 1000.
    """
    if db_uri is None:
        db_uri = get_database_uri()
    
    try:
        engine = create_engine(db_uri, echo=False)
        total_rows_appended = 0
        
        # Check if the CSV file is completely empty (no headers, no data)
        try:
            # Attempt to read just the header to see if the file is parseable and has columns
            # If this fails with EmptyDataError, the file is truly empty or malformed.
            header_df = pd.read_csv(csv_file_path, nrows=0)
            if header_df.empty and not header_df.columns.any(): # No columns implies truly empty or unreadable
                 print(f"Error: The file '{csv_file_path}' is empty or does not contain valid CSV headers.")
                 return
        except pd.errors.EmptyDataError:
            print(f"Error: The file '{csv_file_path}' is empty.")
            return # Exit if the file is completely empty

        for chunk_df in pd.read_csv(csv_file_path, chunksize=chunk_size):
            if chunk_df.empty: 
                continue
            
            chunk_df.to_sql(table_name, engine, if_exists="append", index=False)
            total_rows_appended += len(chunk_df)
        
        db_file_name = db_uri.split("///")[-1] if "///" in db_uri else db_uri
        if total_rows_appended > 0:
            print(f"Successfully appended a total of {total_rows_appended} rows from '{csv_file_path}' to table '{table_name}' in '{db_file_name}'.")
        else:
            print(f"No data rows to append from '{csv_file_path}'. The file might only contain headers or all chunks were empty.")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred while appending data from '{csv_file_path}': {e}")

if __name__ == "__main__":
    # Uses DATABASE_URL from environment if set, otherwise defaults to sqlite:///database.db
    # Set DATABASE_URL in .env file for PostgreSQL:
    # DATABASE_URL=postgresql://user:password@host/dbname
    
    print(f"Using database: {get_database_uri()}")
    
    # Example: Append data from a CSV file
    append_data_from_csv(
        csv_file_path='raw_scores/thi_2026_gymfest_scores.csv',
        table_name='scores'
    )
    
    # Other examples:
    # create_db_from_csv(csv_file_path='your_data.csv', table_name='your_table')
    # append_data_from_csv(csv_file_path='more_data.csv', table_name='scores') 