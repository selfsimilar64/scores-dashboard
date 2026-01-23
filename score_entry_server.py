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
    athletes = [row['AthleteName'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(athletes)

@app.route('/api/recent_meets', methods=['GET'])
def recent_meets():
    """Get list of recent meets for autocomplete."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT MeetName FROM scores ORDER BY MeetName')
    meets = [row['MeetName'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(meets)

@app.route('/api/levels', methods=['GET'])
def get_levels():
    """Get list of levels for selection."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT Level FROM scores ORDER BY Level')
    levels = [row['Level'] for row in cursor.fetchall()]
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
    
    meet_name = recent_meet['MeetName']
    meet_date = recent_meet['MeetDate']
    comp_year = recent_meet['CompYear']
    
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
        athlete = row['AthleteName']
        level = row['Level']
        event = row['Event']
        current_score = row['Score']
        place = row['Place']
        
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
    meets = [{'name': row['MeetName'], 'date': row['MeetDate'], 'year': row['CompYear']} 
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
    
    comp_year = result['CompYear']
    
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
        athlete = row['AthleteName']
        level = row['Level']
        event = row['Event']
        current_score = row['Score']
        place = row['Place']
        
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
    all_comp_years = [row['CompYear'] for row in cursor.fetchall()]
    
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
        name = meet['MeetName'].lower()
        if name == 'states':
            return (1, meet['EarliestDate'])
        elif name == 'regionals':
            return (2, meet['EarliestDate'])
        else:
            return (0, meet['EarliestDate'])
    
    meets = sorted(meets_raw, key=meet_sort_key)
    
    # Define level order
    level_order = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'XB', 'XS', 'XG', 'XP', 'XD', 'XSA']
    
    # Get average All Around score for each meet/level combination
    results = []
    
    for meet in meets:
        meet_name = meet['MeetName']
        earliest_date = meet['EarliestDate']
        meet_comp_year = meet['CompYear']
        
        # Get all dates for this meet name in this comp year
        cursor.execute('''
            SELECT DISTINCT MeetDate FROM scores 
            WHERE MeetName = %s AND CompYear = %s 
            ORDER BY MeetDate
        ''', (meet_name, meet_comp_year))
        meet_dates = [row['MeetDate'] for row in cursor.fetchall()]
        
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
                scores_list = [row['Score'] for row in level_scores]
                avg_score = sum(scores_list) / len(scores_list)
                
                # Top 3 for team score - only if we have at least 3 scores
                if len(level_scores) >= 3:
                    top3 = level_scores[:3]
                    top3_details = [{'athlete': row['AthleteName'], 'score': row['Score']} for row in top3]
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
                all_aa_with_athletes.extend([{'athlete': row['AthleteName'], 'score': row['Score'], 'level': level} for row in level_scores])
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
