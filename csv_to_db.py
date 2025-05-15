import pandas as pd
from sqlalchemy import create_engine

def create_scores_from_csv(csv_file_path: str, db_uri: str = "sqlite:///scores.db", table_name: str = "scores"):
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    # Convert Score and Place columns to numeric, handling errors
    df["Score"] = pd.to_numeric(df["Score"], errors="coerce")
    df["Place"] = pd.to_numeric(df["Place"], errors="coerce")
    # Create SQLite engine and write to database
    engine = create_engine(db_uri, echo=False)
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"Wrote {len(df)} rows to {db_uri.replace('sqlite:///', '')} → table '{table_name}'")

def append_scores_from_csv(csv_file_path: str, db_uri: str = "sqlite:///scores.db", table_name: str = "scores", chunk_size: int = 1000):
    """
    Reads data from a CSV file in chunks and appends it to the specified table in an SQLite database.

    Args:
        csv_file_path (str): The path to the CSV file containing the new scores.
        db_uri (str, optional): The database URI. Defaults to "sqlite:///scores.db".
        table_name (str, optional): The name of the table to append to. Defaults to "scores".
        chunk_size (int, optional): Number of rows per chunk to read from CSV. Defaults to 1000.
    """
    try:
        engine = create_engine(db_uri, echo=False)
        total_rows_appended = 0
        
        for chunk_df in pd.read_csv(csv_file_path, chunksize=chunk_size):
            # Filter by CompYear: only append if CompYear is not 2025
            if "CompYear" in chunk_df.columns:
                # Convert CompYear to numeric, coercing errors. NaN != 2025 will be True.
                comp_year_numeric = pd.to_numeric(chunk_df["CompYear"], errors='coerce')
                # Keep rows where CompYear is not 2025 (or where CompYear was NaN after coercion)
                chunk_df = chunk_df[comp_year_numeric != 2025]
            
            # If chunk is empty after CompYear filter, skip to the next chunk
            if chunk_df.empty:
                continue

            # Process Place column: trim to integer, include only if 1-8
            if "Place" in chunk_df.columns:
                # Ensure 'Place' is treated as string for extraction
                place_str = chunk_df["Place"].astype(str)
                # Extract only the leading integer part (e.g., "T1" -> "1", "8*" -> "8")
                extracted_digits = place_str.str.extract(r'^(\\d+)')[0]
                # Convert extracted digits to numeric, coercing errors (e.g., non-digits) to NaT/NaN
                numeric_place = pd.to_numeric(extracted_digits, errors="coerce")
                
                # Set 'Place' to the numeric value if it's between 1 and 8 (inclusive), otherwise set to pd.NA
                chunk_df["Place"] = numeric_place.where((numeric_place >= 1) & (numeric_place <= 8), pd.NA)

            # Perform the same data type conversions as in the main function for consistency
            if "Score" in chunk_df.columns:
                chunk_df["Score"] = pd.to_numeric(chunk_df["Score"], errors="coerce")
            
            # Convert 'Place' (which may now contain pd.NA) to a final numeric type (e.g., float if NAs are present)
            if "Place" in chunk_df.columns:
                 chunk_df["Place"] = chunk_df["Place"].astype(pd.Int64Dtype()) 
            
            # Only attempt to write to SQL if the chunk is not empty after all filters
            if not chunk_df.empty:
                chunk_df.to_sql(table_name, engine, if_exists="append", index=False)
                total_rows_appended += len(chunk_df)
            # Optional: print progress for each chunk
            # print(f"Appended a chunk of {len(chunk_df)} rows. Total appended so far: {total_rows_appended}.")
        
        if total_rows_appended > 0:
            print(f"Successfully appended a total of {total_rows_appended} rows from '{csv_file_path}' to table '{table_name}' in {db_uri.replace('sqlite:///', '')}.")
        else:
             print(f"No data to append from '{csv_file_path}'. The file might be empty or only contain headers.")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
    except pd.errors.EmptyDataError:
        # This specific error might not be hit directly with chunksize if file is just empty,
        # as the loop over pd.read_csv might not execute.
        print(f"Error: The file '{csv_file_path}' is empty or contains no data rows.")
    except Exception as e:
        print(f"An error occurred while appending data from '{csv_file_path}': {e}")

if __name__ == "__main__":
    # main() 
    append_scores_from_csv("winterfest_2024_scores.csv") 