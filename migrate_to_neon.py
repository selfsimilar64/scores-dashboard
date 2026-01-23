"""
Migration script to transfer data from SQLite to Neon PostgreSQL.

Usage:
1. Create a .env file with your Neon DATABASE_URL
2. Run: python migrate_to_neon.py

This will:
1. Read all data from your local database.db (SQLite)
2. Create the scores table in Neon if it doesn't exist
3. Insert all data into Neon
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB = 'database.db'

def migrate():
    # Get Neon connection string
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment or .env file")
        print("Get your connection string from Neon dashboard and add it to .env:")
        print("DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require")
        return
    
    # Connect to SQLite
    print(f"Reading from SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get all data from SQLite
    sqlite_cursor.execute('SELECT * FROM scores')
    rows = sqlite_cursor.fetchall()
    print(f"Found {len(rows)} rows to migrate")
    
    if len(rows) == 0:
        print("No data to migrate!")
        sqlite_conn.close()
        return
    
    # Connect to PostgreSQL (Neon)
    print("Connecting to Neon PostgreSQL...")
    pg_conn = psycopg2.connect(database_url)
    pg_cursor = pg_conn.cursor()
    
    # Create table if it doesn't exist
    print("Creating scores table if not exists...")
    pg_cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id SERIAL PRIMARY KEY,
            AthleteName VARCHAR(255),
            Level VARCHAR(10),
            CompYear VARCHAR(10),
            MeetName VARCHAR(255),
            MeetDate DATE,
            Event VARCHAR(50),
            StartValue DECIMAL(5,3),
            Score DECIMAL(5,3),
            Place INTEGER
        )
    ''')
    
    # Check if table already has data
    pg_cursor.execute('SELECT COUNT(*) FROM scores')
    existing_count = pg_cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"WARNING: Neon database already has {existing_count} rows.")
        response = input("Do you want to DELETE existing data and replace? (yes/no): ")
        if response.lower() == 'yes':
            pg_cursor.execute('DELETE FROM scores')
            print("Deleted existing data.")
        else:
            print("Aborting migration. Existing data preserved.")
            pg_conn.close()
            sqlite_conn.close()
            return
    
    # Prepare data for insertion
    data = []
    for row in rows:
        data.append((
            row['AthleteName'],
            row['Level'],
            row['CompYear'],
            row['MeetName'],
            row['MeetDate'],
            row['Event'],
            row['StartValue'],
            row['Score'],
            row['Place']
        ))
    
    # Insert data using execute_values for efficiency
    print("Inserting data into Neon...")
    insert_query = '''
        INSERT INTO scores (AthleteName, Level, CompYear, MeetName, MeetDate, Event, StartValue, Score, Place)
        VALUES %s
    '''
    execute_values(pg_cursor, insert_query, data)
    
    # Commit and close
    pg_conn.commit()
    
    # Verify
    pg_cursor.execute('SELECT COUNT(*) FROM scores')
    final_count = pg_cursor.fetchone()[0]
    print(f"Migration complete! {final_count} rows now in Neon database.")
    
    # Create indexes
    print("Creating indexes...")
    pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_athlete ON scores(AthleteName)')
    pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_meet ON scores(MeetName, MeetDate)')
    pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_comp_year ON scores(CompYear)')
    pg_cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores_level ON scores(Level)')
    pg_conn.commit()
    print("Indexes created.")
    
    pg_conn.close()
    sqlite_conn.close()
    
    print("\n✅ Migration successful!")
    print("You can now deploy to Render and your data will be available.")

if __name__ == '__main__':
    migrate()
