"""
Import historical attendance data from Google Sheets CSV exports into Neon database.

This script will:
1. Read CSV files from the 'attendance history' folder
2. Parse dates and attendance status
3. Map athlete names to existing athletes (or create new ones)
4. Import attendance records for Winter 2025 session (ID: 2)

Level mappings:
- 'Level N' -> 'N' (e.g., Level 3 -> 3, Level 4 -> 4)
- Bronze, Silver, Gold, Platinum, Diamond, Sapphire -> XB, XS, XG, XP, XD, XSA

Status mappings:
- 'Present' -> 'present'
- 'Late' -> 'present' with late_minutes=5
- 'Absent' -> 'absent'
- 'Partial' -> 'partial'
- Empty -> skip

Usage:
1. Ensure DATABASE_URL is set in .env
2. Ensure CSV files are in 'attendance history' folder
3. Run: python import_attendance_history.py
"""

import os
import csv
import re
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Session ID for Winter 2025
SESSION_ID = 2

# Level mappings for Xcel levels
XCEL_LEVEL_MAP = {
    'bronze': 'XB',
    'silver': 'XS',
    'gold': 'XG',
    'platinum': 'XP',
    'diamond': 'XD',
    'sapphire': 'XSA',
}

def extract_level_from_filename(filename):
    """Extract level from filename like 'Winter 25 - Gold.csv'."""
    # Remove .csv extension and split by ' - '
    name = filename.replace('.csv', '')
    parts = name.split(' - ')
    if len(parts) >= 2:
        level_part = parts[-1].strip()
        return normalize_level(level_part)
    return None

def normalize_level(level_str):
    """Convert level string to database format."""
    if not level_str:
        return None
    
    level_str = level_str.strip()
    
    # Check for 'Level N' format
    match = re.match(r'Level\s*(\d+)', level_str, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Check for 'N' format (just a number like '4-8')
    if re.match(r'^\d+(-\d+)?$', level_str):
        return level_str
    
    # Check for Xcel levels
    lower = level_str.lower()
    if lower in XCEL_LEVEL_MAP:
        return XCEL_LEVEL_MAP[lower]
    
    return level_str

def parse_date_column(col_header):
    """Parse date from column header like '12-01' to a full date.
    
    Assumes December dates are 2024 and January-March dates are 2025.
    """
    match = re.match(r'^(\d{2})-(\d{2})$', col_header)
    if not match:
        return None
    
    month = int(match.group(1))
    day = int(match.group(2))
    
    # December is 2024, January-March is 2025
    if month >= 10:  # Oct, Nov, Dec
        year = 2024
    else:  # Jan, Feb, Mar, etc.
        year = 2025
    
    try:
        return date(year, month, day)
    except ValueError:
        return None

def parse_status(value):
    """Parse attendance status from CSV value.
    
    Returns (status, late_minutes) tuple.
    """
    if not value or not value.strip():
        return None, 0
    
    val = value.strip().lower()
    
    if val == 'present':
        return 'present', 0
    elif val == 'late':
        return 'present', 5  # Treat Late as Present with 5 minutes late
    elif val == 'absent':
        return 'absent', 0
    elif val == 'partial':
        return 'partial', 0
    else:
        return None, 0

def get_or_create_athlete(cursor, name, level):
    """Get athlete ID by name, creating if necessary."""
    name = name.strip()
    if not name:
        return None
    
    # Try to find existing athlete
    cursor.execute('SELECT id FROM athletes WHERE name = %s', (name,))
    result = cursor.fetchone()
    
    if result:
        return result['id']
    
    # Create new athlete
    cursor.execute(
        'INSERT INTO athletes (name, current_level) VALUES (%s, %s) RETURNING id',
        (name, level)
    )
    new_id = cursor.fetchone()['id']
    print(f"   Created new athlete: {name} (Level {level})")
    return new_id

def process_csv_file(cursor, filepath, default_level):
    """Process a single CSV file and return attendance records."""
    records = []
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        # Find which columns are dates
        date_columns = []
        has_level_column = False
        level_col_idx = None
        name_col_idx = 0
        
        for idx, header in enumerate(headers):
            header_clean = header.strip()
            if header_clean.lower() == 'name':
                name_col_idx = idx
            elif header_clean.lower() == 'level':
                has_level_column = True
                level_col_idx = idx
            else:
                parsed_date = parse_date_column(header_clean)
                if parsed_date:
                    date_columns.append((idx, parsed_date))
        
        # Process each row
        for row in reader:
            if not row or not row[name_col_idx].strip():
                continue
            
            name = row[name_col_idx].strip()
            
            # Get level for this row
            if has_level_column and level_col_idx is not None:
                row_level = normalize_level(row[level_col_idx]) if len(row) > level_col_idx else default_level
                if not row_level:
                    row_level = default_level
            else:
                row_level = default_level
            
            # Get or create athlete
            athlete_id = get_or_create_athlete(cursor, name, row_level)
            if not athlete_id:
                continue
            
            # Process each date column
            for col_idx, practice_date in date_columns:
                if col_idx >= len(row):
                    continue
                
                status, late_minutes = parse_status(row[col_idx])
                if status:
                    records.append({
                        'athlete_id': athlete_id,
                        'session_id': SESSION_ID,
                        'practice_date': practice_date,
                        'level': row_level,
                        'status': status,
                        'late_minutes': late_minutes,
                    })
    
    return records

def import_attendance():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment or .env file")
        return False
    
    print("Connecting to Neon PostgreSQL...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Find CSV files in attendance history folder
    history_dir = os.path.join(os.path.dirname(__file__), 'attendance history')
    if not os.path.exists(history_dir):
        print(f"ERROR: Attendance history folder not found: {history_dir}")
        return False
    
    csv_files = [f for f in os.listdir(history_dir) if f.endswith('.csv')]
    if not csv_files:
        print("ERROR: No CSV files found in attendance history folder")
        return False
    
    print(f"Found {len(csv_files)} CSV files to process")
    
    all_records = []
    
    try:
        for filename in csv_files:
            filepath = os.path.join(history_dir, filename)
            default_level = extract_level_from_filename(filename)
            print(f"\nProcessing: {filename} (default level: {default_level})")
            
            records = process_csv_file(cursor, filepath, default_level)
            all_records.extend(records)
            print(f"   Found {len(records)} attendance records")
        
        print(f"\nTotal records to import: {len(all_records)}")
        
        # Insert records
        inserted = 0
        updated = 0
        
        for rec in all_records:
            cursor.execute('''
                INSERT INTO attendance (athlete_id, session_id, practice_date, level, status, late_minutes, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (athlete_id, practice_date)
                DO UPDATE SET 
                    status = EXCLUDED.status, 
                    late_minutes = EXCLUDED.late_minutes,
                    level = EXCLUDED.level,
                    updated_at = NOW()
                RETURNING (xmax = 0) AS is_insert
            ''', (
                rec['athlete_id'],
                rec['session_id'],
                rec['practice_date'],
                rec['level'],
                rec['status'],
                rec['late_minutes'],
            ))
            result = cursor.fetchone()
            if result['is_insert']:
                inserted += 1
            else:
                updated += 1
        
        conn.commit()
        
        print("\n" + "="*50)
        print("[SUCCESS] Import completed!")
        print("="*50)
        print(f"Records inserted: {inserted}")
        print(f"Records updated: {updated}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        print("Import rolled back. No changes were made.")
        return False
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    import_attendance()
