"""
Migration script to add attendance tracking tables to the Neon database.

This script will:
1. Create a backup of the scores table
2. Create the athletes table and populate from existing scores
3. Create the sessions table (for seasons like Winter, Spring, Summer, Fall)
4. Create the practice_schedules table
5. Create the attendance table

Usage:
1. Ensure DATABASE_URL is set in .env
2. Run: python migrate_attendance.py
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def migrate():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment or .env file")
        return False
    
    print("Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Step 1: Backup the scores table
        print("\n1. Creating backup of scores table...")
        backup_table_name = f"scores_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        cursor.execute(f'CREATE TABLE {backup_table_name} AS SELECT * FROM scores')
        cursor.execute(f'SELECT COUNT(*) as count FROM {backup_table_name}')
        backup_count = cursor.fetchone()['count']
        print(f"   [OK] Backup created: {backup_table_name} ({backup_count} rows)")
        
        # Step 2: Create athletes table
        print("\n2. Creating athletes table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS athletes (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                current_level VARCHAR(10),
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        print("   [OK] Athletes table created")
        
        # Populate athletes from existing scores
        print("   Populating athletes from existing scores...")
        cursor.execute('''
            INSERT INTO athletes (name, current_level)
            SELECT DISTINCT ON (AthleteName) 
                AthleteName, 
                Level
            FROM scores
            ORDER BY AthleteName, MeetDate DESC
            ON CONFLICT (name) DO NOTHING
        ''')
        cursor.execute('SELECT COUNT(*) as count FROM athletes')
        athlete_count = cursor.fetchone()['count']
        print(f"   [OK] Populated {athlete_count} athletes")
        
        # Create index on athletes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_athletes_name ON athletes(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_athletes_level ON athletes(current_level)')
        
        # Step 3: Create sessions table (seasons)
        print("\n3. Creating sessions table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                year INTEGER NOT NULL,
                season VARCHAR(20) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, season)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_year ON sessions(year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_dates ON sessions(start_date, end_date)')
        print("   [OK] Sessions table created")
        
        # Step 4: Create practice_schedules table
        print("\n4. Creating practice_schedules table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS practice_schedules (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                level VARCHAR(10) NOT NULL,
                day_of_week SMALLINT NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(session_id, level, day_of_week)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_session ON practice_schedules(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_level ON practice_schedules(level)')
        print("   [OK] Practice schedules table created")
        
        # Step 5: Create attendance table
        print("\n5. Creating attendance table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                practice_date DATE NOT NULL,
                level VARCHAR(10) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'none',
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(athlete_id, practice_date)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_athlete ON attendance(athlete_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(practice_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_level ON attendance(level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_status ON attendance(status)')
        print("   [OK] Attendance table created")
        
        # Step 6: Create athlete_notes table for injuries/milestones
        print("\n6. Creating athlete_notes table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS athlete_notes (
                id SERIAL PRIMARY KEY,
                athlete_id INTEGER REFERENCES athletes(id) ON DELETE CASCADE,
                note_date DATE NOT NULL,
                category VARCHAR(50) DEFAULT 'general',
                note TEXT NOT NULL,
                resolved_date DATE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_athlete ON athlete_notes(athlete_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notes_date ON athlete_notes(note_date)')
        print("   [OK] Athlete notes table created")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*50)
        print("[SUCCESS] Migration completed successfully!")
        print("="*50)
        print(f"\nBackup table: {backup_table_name}")
        print(f"Athletes imported: {athlete_count}")
        print("\nNew tables created:")
        print("  - athletes")
        print("  - sessions")
        print("  - practice_schedules")
        print("  - attendance")
        print("  - athlete_notes")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR]: {e}")
        print("Migration rolled back. No changes were made.")
        return False
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    migrate()
