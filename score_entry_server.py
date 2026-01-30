"""
Flask server for score entry interface.
Run with: python score_entry_server.py
Access at: http://localhost:5050

For local development, create a .env file with:
DATABASE_URL=postgresql://user:password@host/dbname
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

app = Flask(__name__, static_folder='score_entry_ui')

# Enable CORS for local development
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Database connection - uses DATABASE_URL environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def serialize_row(row):
    """Convert a database row to a JSON-serializable dict."""
    from datetime import date, time, datetime
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        elif isinstance(value, time):
            result[key] = str(value)
    return result

def serialize_rows(rows):
    """Convert multiple database rows to JSON-serializable dicts."""
    return [serialize_row(row) for row in rows]

@app.route('/')
def index():
    return send_from_directory('score_entry_ui', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('score_entry_ui', path)

@app.route('/api/submit_scores', methods=['POST'])
def submit_scores():
    """
    Submit scores for an athlete.
    Expects JSON with:
    - meetName, meetDate, compYear (session-level)
    - athleteName
    - level
    - events: array of {event, score, place} objects
    """
    data = request.json
    
    meet_name = data.get('meetName')
    meet_date = data.get('meetDate')
    comp_year = data.get('compYear')
    athlete_name = data.get('athleteName')
    level = data.get('level')
    events = data.get('events', [])
    
    if not all([meet_name, meet_date, comp_year, athlete_name, level]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted_count = 0
    for event_data in events:
        event_name = event_data.get('event')
        score = event_data.get('score')
        place = event_data.get('place')
        
        # Only insert if score is provided
        if score is not None and score != '':
            try:
                score_value = float(score)
                place_value = int(place) if place else None
                
                cursor.execute('''
                    INSERT INTO scores (AthleteName, Level, CompYear, MeetName, MeetDate, Event, StartValue, Score, Place)
                    VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s)
                ''', (athlete_name, level, comp_year, meet_name, meet_date, event_name, score_value, place_value))
                inserted_count += 1
            except (ValueError, TypeError) as e:
                continue  # Skip invalid scores
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': f'Inserted {inserted_count} score(s) for {athlete_name}',
        'inserted_count': inserted_count
    })

@app.route('/api/recent_athletes', methods=['GET'])
def recent_athletes():
    """Get list of recent athlete names for autocomplete."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT AthleteName FROM scores ORDER BY AthleteName')
    athletes = [row['athletename'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(athletes)

@app.route('/api/recent_meets', methods=['GET'])
def recent_meets():
    """Get list of recent meets for autocomplete."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT MeetName FROM scores ORDER BY MeetName')
    meets = [row['meetname'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(meets)

@app.route('/api/levels', methods=['GET'])
def get_levels():
    """Get list of levels for selection."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT Level FROM scores ORDER BY Level')
    levels = [row['level'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(levels)

@app.route('/personal-bests')
def personal_bests_page():
    return send_from_directory('score_entry_ui', 'personal_bests.html')

@app.route('/api/personal_bests', methods=['GET'])
def get_personal_bests():
    """
    Get personal bests achieved at the most recent meet.
    A PB is when an athlete's score for an event exceeds all their previous
    scores for that event in the same CompYear.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the most recent meet
    cursor.execute('''
        SELECT MeetName, MeetDate, CompYear 
        FROM scores 
        ORDER BY MeetDate DESC 
        LIMIT 1
    ''')
    recent_meet = cursor.fetchone()
    
    if not recent_meet:
        conn.close()
        return jsonify({'error': 'No meets found', 'personal_bests': []})
    
    meet_name = recent_meet['meetname']
    meet_date = recent_meet['meetdate']
    comp_year = recent_meet['compyear']
    
    # Get all scores from the most recent meet
    cursor.execute('''
        SELECT AthleteName, Level, Event, Score, Place
        FROM scores
        WHERE MeetName = %s AND MeetDate = %s
        ORDER BY AthleteName, Event
    ''', (meet_name, meet_date))
    
    current_scores = cursor.fetchall()
    
    personal_bests = []
    
    for row in current_scores:
        athlete = row['athletename']
        level = row['level']
        event = row['event']
        current_score = row['score']
        place = row['place']
        
        if current_score is None:
            continue
        
        # Get the max score for this athlete/event from PREVIOUS meets in the same CompYear
        cursor.execute('''
            SELECT MAX(Score) as prev_best
            FROM scores
            WHERE AthleteName = %s 
              AND Event = %s 
              AND CompYear = %s
              AND MeetDate < %s
              AND Score IS NOT NULL
        ''', (athlete, event, comp_year, meet_date))
        
        prev_result = cursor.fetchone()
        prev_best = prev_result['prev_best'] if prev_result else None
        
        # It's a PB if there's no previous score OR current score is higher
        is_pb = prev_best is None or current_score > prev_best
        
        if is_pb:
            personal_bests.append({
                'athlete': athlete,
                'level': level,
                'event': event,
                'score': current_score,
                'place': place,
                'previous_best': prev_best,
                'improvement': round(current_score - prev_best, 3) if prev_best else None,
                'is_first_meet': prev_best is None
            })
    
    conn.close()
    
    return jsonify({
        'meet_name': meet_name,
        'meet_date': meet_date,
        'comp_year': comp_year,
        'personal_bests': personal_bests
    })

@app.route('/api/meets', methods=['GET'])
def get_meets():
    """Get list of all meets ordered by date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT MeetName, MeetDate, CompYear 
        FROM scores 
        ORDER BY MeetDate DESC
    ''')
    meets = [{'name': row['meetname'], 'date': row['meetdate'], 'year': row['compyear']} 
             for row in cursor.fetchall()]
    conn.close()
    return jsonify(meets)

@app.route('/api/meet_scores', methods=['GET'])
def get_meet_scores():
    """Get all scores for a specific meet with PB status."""
    meet_name = request.args.get('meet_name')
    meet_date = request.args.get('meet_date')
    
    if not meet_name or not meet_date:
        return jsonify({'error': 'meet_name and meet_date required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the CompYear for this meet
    cursor.execute('''
        SELECT CompYear FROM scores 
        WHERE MeetName = %s AND MeetDate = %s 
        LIMIT 1
    ''', (meet_name, meet_date))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return jsonify({'error': 'Meet not found', 'scores': []})
    
    comp_year = result['compyear']
    
    # Get all scores from the specified meet
    cursor.execute('''
        SELECT AthleteName, Level, Event, Score, Place
        FROM scores
        WHERE MeetName = %s AND MeetDate = %s
        ORDER BY AthleteName, Event
    ''', (meet_name, meet_date))
    
    current_scores = cursor.fetchall()
    
    all_scores = []
    
    for row in current_scores:
        athlete = row['athletename']
        level = row['level']
        event = row['event']
        current_score = row['score']
        place = row['place']
        
        if current_score is None:
            all_scores.append({
                'athlete': athlete,
                'level': level,
                'event': event,
                'score': None,
                'place': place
            })
            continue
        
        # Get best score THIS YEAR (same CompYear, before this meet)
        cursor.execute('''
            SELECT Score as best, MeetName as meet_name, MeetDate as meet_date
            FROM scores
            WHERE AthleteName = %s 
              AND Event = %s 
              AND CompYear = %s
              AND MeetDate < %s
              AND Score IS NOT NULL
            ORDER BY Score DESC
            LIMIT 1
        ''', (athlete, event, comp_year, meet_date))
        
        year_result = cursor.fetchone()
        year_best = year_result['best'] if year_result else None
        year_best_meet = year_result['meet_name'] if year_result else None
        year_best_date = year_result['meet_date'] if year_result else None
        
        # Get best score from PREVIOUS COMP YEARS at this level (not this year)
        cursor.execute('''
            SELECT Score as best, MeetName as meet_name, MeetDate as meet_date
            FROM scores
            WHERE AthleteName = %s 
              AND Event = %s 
              AND Level = %s
              AND CompYear != %s
              AND Score IS NOT NULL
            ORDER BY Score DESC
            LIMIT 1
        ''', (athlete, event, level, comp_year))
        
        prev_year_result = cursor.fetchone()
        prev_year_best = prev_year_result['best'] if prev_year_result else None
        prev_year_best_meet = prev_year_result['meet_name'] if prev_year_result else None
        prev_year_best_date = prev_year_result['meet_date'] if prev_year_result else None
        
        # Calculate the TRUE all-time best at this level (including current year)
        # This is the max of year_best and prev_year_best
        if year_best is not None and prev_year_best is not None:
            if year_best >= prev_year_best:
                alltime_best = year_best
                alltime_best_meet = year_best_meet
                alltime_best_date = year_best_date
            else:
                alltime_best = prev_year_best
                alltime_best_meet = prev_year_best_meet
                alltime_best_date = prev_year_best_date
        elif year_best is not None:
            alltime_best = year_best
            alltime_best_meet = year_best_meet
            alltime_best_date = year_best_date
        elif prev_year_best is not None:
            alltime_best = prev_year_best
            alltime_best_meet = prev_year_best_meet
            alltime_best_date = prev_year_best_date
        else:
            alltime_best = None
            alltime_best_meet = None
            alltime_best_date = None
        
        # Determine status flags
        is_first_year_at_level = prev_year_best is None  # No scores from previous years at this level
        is_first_meet_of_year = year_best is None  # No scores from earlier this year
        
        # TURQUOISE: All-time PB at level (returning athlete beat ALL previous including this year)
        # Conditions:
        # 1. Must be second+ year at level (has previous year scores)
        # 2. Current score STRICTLY > all-time best (which includes this year)
        is_alltime_pb = (
            not is_first_year_at_level  # returning at this level
            and alltime_best is not None
            and current_score > alltime_best  # strictly beat the all-time best
        )
        
        # GOLD: Year PB (beat all previous scores this year)
        # Conditions:
        # 1. Must NOT be first meet of the year (no gold at first meet)
        # 2. Current score STRICTLY > this year's best
        # Note: Can overlap with turquoise - frontend will prioritize turquoise
        is_year_pb = (
            not is_first_meet_of_year  # not first meet of year
            and current_score > year_best  # strictly beat this year's previous best
        )
        
        all_scores.append({
            'athlete': athlete,
            'level': level,
            'event': event,
            'score': current_score,
            'place': place,
            'is_first_year_at_level': is_first_year_at_level,
            'is_first_meet_of_year': is_first_meet_of_year,
            'is_year_pb': is_year_pb,
            'is_alltime_pb': is_alltime_pb,
            'year_best': year_best,
            'year_best_meet': year_best_meet,
            'year_best_date': year_best_date,
            'alltime_best': alltime_best,
            'alltime_best_meet': alltime_best_meet,
            'alltime_best_date': alltime_best_date,
            'year_improvement': round(current_score - year_best, 3) if year_best and is_year_pb else None,
            'alltime_improvement': round(current_score - alltime_best, 3) if alltime_best and is_alltime_pb else None
        })
    
    conn.close()
    
    return jsonify({
        'meet_name': meet_name,
        'meet_date': meet_date,
        'comp_year': comp_year,
        'scores': all_scores
    })

@app.route('/meet-averages')
def meet_averages_page():
    return send_from_directory('score_entry_ui', 'meet_averages.html')

@app.route('/api/meet_level_averages', methods=['GET'])
def get_meet_level_averages():
    """Get average All Around scores by Meet and Level."""
    comp_year = request.args.get('comp_year', '2026')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all comp years for the dropdown
    cursor.execute('SELECT DISTINCT CompYear FROM scores ORDER BY CompYear DESC')
    all_comp_years = [row['compyear'] for row in cursor.fetchall()]
    
    # Get all unique meet names for the selected comp year, with their earliest date for sorting
    cursor.execute('''
        SELECT MeetName, MIN(MeetDate) as EarliestDate, CompYear
        FROM scores
        WHERE CompYear = %s
        GROUP BY MeetName, CompYear
        ORDER BY MIN(MeetDate) ASC
    ''', (comp_year,))
    meets_raw = cursor.fetchall()
    
    # Sort with States and Regionals at the end (States before Regionals)
    def meet_sort_key(meet):
        name = meet['meetname'].lower()
        if name == 'states':
            return (1, meet['earliestdate'])
        elif name == 'regionals':
            return (2, meet['earliestdate'])
        else:
            return (0, meet['earliestdate'])
    
    meets = sorted(meets_raw, key=meet_sort_key)
    
    # Define level order
    level_order = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'XB', 'XS', 'XG', 'XP', 'XD', 'XSA']
    
    # Get average All Around score for each meet/level combination
    results = []
    
    for meet in meets:
        meet_name = meet['meetname']
        earliest_date = meet['earliestdate']
        meet_comp_year = meet['compyear']
        
        # Get all dates for this meet name in this comp year
        cursor.execute('''
            SELECT DISTINCT MeetDate FROM scores 
            WHERE MeetName = %s AND CompYear = %s 
            ORDER BY MeetDate
        ''', (meet_name, meet_comp_year))
        meet_dates = [row['meetdate'] for row in cursor.fetchall()]
        
        meet_data = {
            'meet_name': meet_name,
            'meet_dates': meet_dates,
            'earliest_date': earliest_date,
            'comp_year': meet_comp_year,
            'levels': {},
            'gymfest_avg': None,
            'gymfest_count': 0
        }
        
        # Get averages and team scores for each level
        all_aa_scores = []  # All scores for Gymfest average
        all_aa_with_athletes = []  # All scores with athlete info for Gymfest team score
        
        for level in level_order:
            # Get all AA scores for this level across all dates for this meet, ordered by score descending
            cursor.execute('''
                SELECT AthleteName, Score
                FROM scores
                WHERE MeetName = %s 
                  AND CompYear = %s
                  AND Level = %s
                  AND Event = 'All Around'
                  AND Score IS NOT NULL
                ORDER BY Score DESC
            ''', (meet_name, meet_comp_year, level))
            
            level_scores = cursor.fetchall()
            
            if level_scores:
                scores_list = [row['score'] for row in level_scores]
                avg_score = sum(scores_list) / len(scores_list)
                
                # Top 3 for team score - only if we have at least 3 scores
                if len(level_scores) >= 3:
                    top3 = level_scores[:3]
                    top3_details = [{'athlete': row['athletename'], 'score': row['score']} for row in top3]
                    team_score = sum(item['score'] for item in top3_details)
                else:
                    top3_details = None
                    team_score = None
                
                meet_data['levels'][level] = {
                    'avg': avg_score,  # Don't round - let frontend handle display rounding
                    'count': len(scores_list),
                    'team_score': team_score,  # None if fewer than 3 scores
                    'top3': top3_details
                }
                
                # Collect for Gymfest calculations
                all_aa_scores.extend(scores_list)
                all_aa_with_athletes.extend([{'athlete': row['athletename'], 'score': row['score'], 'level': level} for row in level_scores])
            else:
                meet_data['levels'][level] = None
        
        # Calculate Gymfest (all levels combined) average and team score
        if all_aa_scores:
            meet_data['gymfest_avg'] = sum(all_aa_scores) / len(all_aa_scores)
            meet_data['gymfest_count'] = len(all_aa_scores)
            
            # Gymfest team score: top 3 across ALL levels - only if we have at least 3 scores
            if len(all_aa_with_athletes) >= 3:
                all_aa_with_athletes.sort(key=lambda x: x['score'], reverse=True)
                gymfest_top3 = all_aa_with_athletes[:3]
                meet_data['gymfest_top3'] = gymfest_top3
                meet_data['gymfest_team_score'] = sum(item['score'] for item in gymfest_top3)
            else:
                meet_data['gymfest_top3'] = None
                meet_data['gymfest_team_score'] = None
        
        results.append(meet_data)
    
    conn.close()
    
    # Determine which levels have any data
    levels_with_data = []
    for level in level_order:
        for meet in results:
            if meet['levels'].get(level) is not None:
                levels_with_data.append(level)
                break
    
    return jsonify({
        'level_order': levels_with_data,
        'all_comp_years': all_comp_years,
        'comp_year': comp_year,
        'meets': results
    })

# ============================================================
# ATTENDANCE TRACKING ENDPOINTS
# ============================================================

@app.route('/attendance')
def attendance_page():
    return send_from_directory('score_entry_ui', 'attendance.html')

@app.route('/api/athletes', methods=['GET'])
def get_athletes():
    """Get all athletes, optionally filtered by level."""
    level = request.args.get('level')
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT id, name, current_level, active FROM athletes WHERE 1=1'
    params = []
    
    if level:
        query += ' AND current_level = %s'
        params.append(level)
    
    if active_only:
        query += ' AND active = TRUE'
    
    query += ' ORDER BY name'
    
    cursor.execute(query, params)
    athletes = cursor.fetchall()
    conn.close()
    
    return jsonify(serialize_rows(athletes))

@app.route('/api/athletes/<int:athlete_id>', methods=['PUT'])
def update_athlete(athlete_id):
    """Update an athlete's details."""
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if 'current_level' in data:
        updates.append('current_level = %s')
        params.append(data['current_level'])
    if 'active' in data:
        updates.append('active = %s')
        params.append(data['active'])
    if 'name' in data:
        updates.append('name = %s')
        params.append(data['name'])
    
    if updates:
        params.append(athlete_id)
        cursor.execute(f"UPDATE athletes SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/athletes', methods=['POST'])
def create_athlete():
    """Create a new athlete."""
    data = request.json
    name = data.get('name')
    level = data.get('current_level')
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO athletes (name, current_level) VALUES (%s, %s) RETURNING id',
            (name, level)
        )
        new_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 400

# Sessions (Seasons) endpoints
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions (seasons)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sessions ORDER BY year DESC, start_date DESC')
    sessions = cursor.fetchall()
    conn.close()
    return jsonify(serialize_rows(sessions))

@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Create a new session (season)."""
    data = request.json
    name = data.get('name')
    year = data.get('year')
    season = data.get('season')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not all([name, year, season, start_date, end_date]):
        return jsonify({'error': 'All fields required: name, year, season, start_date, end_date'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO sessions (name, year, season, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (name, year, season, start_date, end_date))
        new_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 400

@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
def update_session(session_id):
    """Update a session."""
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE sessions SET name = %s, year = %s, season = %s, start_date = %s, end_date = %s
        WHERE id = %s
    ''', (data['name'], data['year'], data['season'], data['start_date'], data['end_date'], session_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/sessions/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session and its schedules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE id = %s', (session_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/sessions/current', methods=['GET'])
def get_current_session():
    """Get the current active session based on today's date."""
    from datetime import date
    today = date.today()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM sessions 
        WHERE start_date <= %s AND end_date >= %s
        ORDER BY start_date DESC
        LIMIT 1
    ''', (today, today))
    session = cursor.fetchone()
    conn.close()
    
    if session:
        return jsonify(serialize_row(session))
    return jsonify(None)

# Practice Schedules endpoints
@app.route('/api/practice_schedules', methods=['GET'])
def get_practice_schedules():
    """Get practice schedules, optionally filtered by session."""
    session_id = request.args.get('session_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute('''
            SELECT ps.*, s.name as session_name 
            FROM practice_schedules ps
            JOIN sessions s ON ps.session_id = s.id
            WHERE ps.session_id = %s
            ORDER BY ps.level, ps.day_of_week
        ''', (session_id,))
    else:
        cursor.execute('''
            SELECT ps.*, s.name as session_name 
            FROM practice_schedules ps
            JOIN sessions s ON ps.session_id = s.id
            ORDER BY s.year DESC, ps.level, ps.day_of_week
        ''')
    
    schedules = cursor.fetchall()
    conn.close()
    return jsonify(serialize_rows(schedules))

@app.route('/api/practice_schedules', methods=['POST'])
def create_practice_schedule():
    """Create a new practice schedule."""
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO practice_schedules (session_id, level, day_of_week, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (data['session_id'], data['level'], data['day_of_week'], data['start_time'], data['end_time']))
        new_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': new_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 400

@app.route('/api/practice_schedules/<int:schedule_id>', methods=['DELETE'])
def delete_practice_schedule(schedule_id):
    """Delete a practice schedule."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM practice_schedules WHERE id = %s', (schedule_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/todays_practice', methods=['GET'])
def get_todays_practice():
    """Get which levels have practice today and the athletes for each level."""
    from datetime import date
    today = date.today()
    day_of_week = today.weekday()  # 0=Monday in Python, but we store 0=Sunday
    # Convert Python's weekday (Mon=0) to our format (Sun=0)
    day_of_week = (day_of_week + 1) % 7
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current session
    cursor.execute('''
        SELECT * FROM sessions 
        WHERE start_date <= %s AND end_date >= %s
        LIMIT 1
    ''', (today, today))
    current_session = cursor.fetchone()
    
    if not current_session:
        conn.close()
        return jsonify({'error': 'No active session', 'levels': []})
    
    # Get levels that practice today
    cursor.execute('''
        SELECT DISTINCT level, start_time, end_time
        FROM practice_schedules
        WHERE session_id = %s AND day_of_week = %s
        ORDER BY level
    ''', (current_session['id'], day_of_week))
    
    levels_today = cursor.fetchall()
    
    result = {
        'date': today.isoformat(),
        'day_of_week': day_of_week,
        'session': serialize_row(current_session),
        'levels': []
    }
    
    for level_row in levels_today:
        level = level_row['level']
        
        # Get athletes at this level
        cursor.execute('''
            SELECT id, name, current_level 
            FROM athletes 
            WHERE current_level = %s AND active = TRUE
            ORDER BY name
        ''', (level,))
        athletes = cursor.fetchall()
        
        # Get existing attendance records for today
        cursor.execute('''
            SELECT athlete_id, status, notes, late_minutes
            FROM attendance
            WHERE practice_date = %s AND level = %s
        ''', (today, level))
        attendance_records = {row['athlete_id']: {'status': row['status'], 'notes': row['notes'], 'late_minutes': row['late_minutes']} 
                            for row in cursor.fetchall()}
        
        athletes_with_attendance = []
        for athlete in athletes:
            att = attendance_records.get(athlete['id'], {'status': 'none', 'notes': None, 'late_minutes': 0})
            athletes_with_attendance.append({
                'id': athlete['id'],
                'name': athlete['name'],
                'status': att['status'],
                'notes': att['notes'],
                'late_minutes': att['late_minutes'] or 0
            })
        
        result['levels'].append({
            'level': level,
            'start_time': str(level_row['start_time']),
            'end_time': str(level_row['end_time']),
            'athletes': athletes_with_attendance
        })
    
    conn.close()
    return jsonify(result)

@app.route('/api/attendance', methods=['POST'])
def record_attendance():
    """Record or update attendance for an athlete."""
    data = request.json
    athlete_id = data.get('athlete_id')
    practice_date = data.get('practice_date')
    level = data.get('level')
    status = data.get('status', 'none')
    notes = data.get('notes')
    late_minutes = data.get('late_minutes', 0)
    session_id = data.get('session_id')
    
    if not all([athlete_id, practice_date, level]):
        return jsonify({'error': 'athlete_id, practice_date, and level are required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # If no session_id provided, find the current session
    if not session_id:
        cursor.execute('''
            SELECT id FROM sessions 
            WHERE start_date <= %s AND end_date >= %s
            LIMIT 1
        ''', (practice_date, practice_date))
        session_row = cursor.fetchone()
        session_id = session_row['id'] if session_row else None
    
    try:
        # Upsert attendance record
        cursor.execute('''
            INSERT INTO attendance (athlete_id, session_id, practice_date, level, status, notes, late_minutes, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (athlete_id, practice_date)
            DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes, late_minutes = EXCLUDED.late_minutes, updated_at = NOW()
            RETURNING id
        ''', (athlete_id, session_id, practice_date, level, status, notes, late_minutes))
        
        record_id = cursor.fetchone()['id']
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': record_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 400

@app.route('/api/attendance/session/<int:session_id>', methods=['GET'])
def get_session_attendance(session_id):
    """Get all attendance data for a session, structured like the Google Sheet."""
    level = request.args.get('level')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get session info
    cursor.execute('SELECT * FROM sessions WHERE id = %s', (session_id,))
    session = cursor.fetchone()
    
    if not session:
        conn.close()
        return jsonify({'error': 'Session not found'}), 404
    
    # Get practice schedules for this session
    schedule_query = '''
        SELECT DISTINCT level, day_of_week 
        FROM practice_schedules 
        WHERE session_id = %s
    '''
    schedule_params = [session_id]
    if level:
        schedule_query += ' AND level = %s'
        schedule_params.append(level)
    
    cursor.execute(schedule_query, schedule_params)
    schedules = cursor.fetchall()
    
    # Build list of scheduled practice days within the session
    from datetime import timedelta
    
    schedule_by_level = {}
    for s in schedules:
        if s['level'] not in schedule_by_level:
            schedule_by_level[s['level']] = set()
        schedule_by_level[s['level']].add(s['day_of_week'])
    
    # Generate all practice dates for each level
    practice_dates_by_level = {}
    current_date = session['start_date']
    end_date = session['end_date']
    
    from datetime import date
    today = date.today()
    if end_date > today:
        end_date = today  # Don't show future dates
    
    while current_date <= end_date:
        dow = (current_date.weekday() + 1) % 7  # Convert to Sun=0 format
        for lvl, days in schedule_by_level.items():
            if dow in days:
                if lvl not in practice_dates_by_level:
                    practice_dates_by_level[lvl] = []
                practice_dates_by_level[lvl].append(current_date)
        current_date += timedelta(days=1)
    
    # Get all attendance records for this session
    att_query = 'SELECT * FROM attendance WHERE session_id = %s'
    att_params = [session_id]
    if level:
        att_query += ' AND level = %s'
        att_params.append(level)
    
    cursor.execute(att_query, att_params)
    attendance_records = cursor.fetchall()
    
    # Index attendance by (athlete_id, date)
    attendance_index = {}
    for rec in attendance_records:
        key = (rec['athlete_id'], rec['practice_date'])
        attendance_index[key] = rec
    
    # Get athletes
    athlete_query = 'SELECT * FROM athletes WHERE active = TRUE'
    athlete_params = []
    if level:
        athlete_query += ' AND current_level = %s'
        athlete_params.append(level)
    athlete_query += ' ORDER BY current_level, name'
    
    cursor.execute(athlete_query, athlete_params if athlete_params else None)
    athletes = cursor.fetchall()
    
    # Build the result structure
    result = {
        'session': serialize_row(session),
        'levels': {}
    }
    
    for athlete in athletes:
        lvl = athlete['current_level']
        if lvl not in result['levels']:
            result['levels'][lvl] = {
                'dates': [d.isoformat() for d in practice_dates_by_level.get(lvl, [])],
                'athletes': []
            }
        
        dates = practice_dates_by_level.get(lvl, [])
        attendance_data = []
        present_count = 0
        total_count = len(dates)
        
        # Day of week counts for percentage calc
        dow_counts = {i: {'present': 0, 'total': 0} for i in range(7)}
        
        for d in dates:
            key = (athlete['id'], d)
            rec = attendance_index.get(key)
            dow = (d.weekday() + 1) % 7
            dow_counts[dow]['total'] += 1
            
            if rec:
                status = rec['status']
                # Present counts as 1, Partial counts as 0.5
                if status == 'present':
                    present_count += 1
                    dow_counts[dow]['present'] += 1
                elif status == 'partial':
                    present_count += 0.5
                    dow_counts[dow]['present'] += 0.5
                attendance_data.append({
                    'date': d.isoformat(),
                    'status': status,
                    'notes': rec['notes'],
                    'late_minutes': rec.get('late_minutes', 0)
                })
            else:
                attendance_data.append({
                    'date': d.isoformat(),
                    'status': 'none',
                    'notes': None,
                    'late_minutes': 0
                })
        
        # Calculate percentages
        total_pct = (present_count / total_count * 100) if total_count > 0 else 0
        dow_pcts = {}
        day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        for dow, counts in dow_counts.items():
            if counts['total'] > 0:
                dow_pcts[day_names[dow]] = round(counts['present'] / counts['total'] * 100, 1)
        
        result['levels'][lvl]['athletes'].append({
            'id': athlete['id'],
            'name': athlete['name'],
            'attendance': attendance_data,
            'total_pct': round(total_pct, 1),
            'dow_pcts': dow_pcts
        })
    
    conn.close()
    return jsonify(result)

@app.route('/api/attendance/bulk', methods=['POST'])
def bulk_record_attendance():
    """Record attendance for multiple athletes at once."""
    data = request.json
    records = data.get('records', [])
    
    if not records:
        return jsonify({'error': 'No records provided'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    success_count = 0
    errors = []
    
    for rec in records:
        try:
            athlete_id = rec.get('athlete_id')
            practice_date = rec.get('practice_date')
            level = rec.get('level')
            status = rec.get('status', 'none')
            notes = rec.get('notes')
            session_id = rec.get('session_id')
            
            if not all([athlete_id, practice_date, level]):
                errors.append({'record': rec, 'error': 'Missing required fields'})
                continue
            
            # Find session if not provided
            if not session_id:
                cursor.execute('''
                    SELECT id FROM sessions 
                    WHERE start_date <= %s AND end_date >= %s
                    LIMIT 1
                ''', (practice_date, practice_date))
                session_row = cursor.fetchone()
                session_id = session_row['id'] if session_row else None
            
            cursor.execute('''
                INSERT INTO attendance (athlete_id, session_id, practice_date, level, status, notes, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (athlete_id, practice_date)
                DO UPDATE SET status = EXCLUDED.status, notes = EXCLUDED.notes, updated_at = NOW()
            ''', (athlete_id, session_id, practice_date, level, status, notes))
            success_count += 1
            
        except Exception as e:
            errors.append({'record': rec, 'error': str(e)})
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'inserted': success_count,
        'errors': errors
    })


if __name__ == '__main__':
    # Ensure the UI folder exists
    os.makedirs('score_entry_ui', exist_ok=True)
    
    # Use PORT from environment (Render sets this) or default to 5050 for local dev
    port = int(os.environ.get('PORT', 5050))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print("\n" + "="*50)
    print("  Score Entry Server")
    print(f"  Open in browser: http://localhost:{port}")
    print("="*50 + "\n")
    app.run(debug=debug, port=port, host='0.0.0.0')
