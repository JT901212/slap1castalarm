from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import extract
from datetime import datetime, time, timedelta
from collections import Counter, defaultdict
import json
import csv
import os
import threading
import time
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("alarm_monitor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AlarmMonitor")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plc_alarms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def load_alarm_definitions(csv_file="alarm_definitions.csv"):
    """
    CSVファイルからアラーム定義を読み込む
    """
    alarm_codes = {}
    d_to_m_today = {}
    d_to_m_yesterday = {}
    
    try:
        if os.path.exists(csv_file):
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if len(row) >= 2:
                        m_code = row[0].strip()
                        description = row[1].strip()
                        alarm_codes[m_code] = description
        else:
            logger.warning(f"Alarm definition file {csv_file} not found. Using default values.")
            for i in range(100):
                m_code = f"M{800+i}"
                alarm_codes[m_code] = f"Alarm {m_code}"
    except Exception as e:
        logger.error(f"Error loading alarm definitions: {e}")
        for i in range(100):
            m_code = f"M{800+i}"
            alarm_codes[m_code] = f"Alarm {m_code}"
    
    d_to_m_today = {f"D{5000+i}": f"M{800+i}" for i in range(100)}
    d_to_m_yesterday = {f"D{5100+i}": f"M{800+i}" for i in range(100)}
    
    return alarm_codes, d_to_m_today, d_to_m_yesterday

ALARM_CODES, D_TO_M_TODAY, D_TO_M_YESTERDAY = load_alarm_definitions()



PLC_CONFIG = {
    '1A': {
        'name': 'Casting_1A',
        'ip': '192.168.150.22'
    },
    '1B': {
        'name': 'Casting_1B',
        'ip': '192.168.150.24'
    }
}

def fetch_alarm_data_from_master(plc_id):
    """Fetch alarm data from PLC Monitor Master API"""
    try:
        registers = ','.join([f'D{5000+i}' for i in range(100)])
        url = f"http://localhost:8000/api/plc/{plc_id}/registers?registers={registers}"
        logger.info(f"Fetching data from master for PLC {plc_id}: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get data from master for PLC {plc_id}: {e}")
        return None

def process_alarm_data(plc_id, alarm_data):
    """Process alarm data and store in database"""
    if not alarm_data:
        return 0
        
    timestamp = datetime.now()
    plc_name = PLC_CONFIG[plc_id]['name']
    
    if plc_id not in LAST_ALARM_VALUES:
        LAST_ALARM_VALUES[plc_id] = {}
    
    recorded_alarms = 0
    
    for d_code, current_value in alarm_data.items():
        current_value = int(current_value)
        last_value = LAST_ALARM_VALUES[plc_id].get(d_code, 0)
        
        if current_value > 0:
            if d_code in D_TO_M_TODAY:
                m_code = D_TO_M_TODAY[d_code]
                description = ALARM_CODES.get(m_code, "Unknown alarm")
                
                if current_value != last_value:
                    ALARM_COUNTS[plc_id][d_code] = current_value
                    
                    alarm = AlarmRecord(
                        timestamp=timestamp,
                        alarm_code=m_code,
                        alarm_description=description,
                        plc_id=plc_id,
                        plc_name=plc_name,
                        count_value=current_value
                    )
                    db.session.add(alarm)
                    recorded_alarms += 1
        
        LAST_ALARM_VALUES[plc_id][d_code] = current_value
    
    db.session.commit()
    return recorded_alarms

def data_collection_loop():
    """Background thread to collect data from master API"""
    PLC_IDS = ['1A', '1B']
    logger.info("Starting PLC data collection thread")
    
    while True:
        try:
            for plc_id in PLC_IDS:
                alarm_data = fetch_alarm_data_from_master(plc_id)
                if alarm_data:
                    with app.app_context():
                        recorded = process_alarm_data(plc_id, alarm_data)
                        if recorded > 0:
                            logger.info(f"Recorded {recorded} alarm events for PLC {plc_id}")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error in data collection loop: {e}")
            time.sleep(10)

LAST_ALARM_VALUES = {}

ALARM_COUNTS = defaultdict(lambda: defaultdict(int))

class AlarmRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    alarm_code = db.Column(db.String(10), nullable=False)
    alarm_description = db.Column(db.String(100), nullable=False)
    plc_id = db.Column(db.String(10), nullable=False)
    plc_name = db.Column(db.String(50), nullable=False)
    count_value = db.Column(db.Integer, default=1)
    
    def __repr__(self):
        return f'<Alarm {self.alarm_code} at {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'alarm_code': self.alarm_code,
            'alarm_description': self.alarm_description,
            'plc_id': self.plc_id,
            'plc_name': self.plc_name,
            'count_value': self.count_value
        }

def get_day_boundaries(target_date=None):
    """Get the start and end of the day (7am to 7am)"""
    if target_date is None:
        target_date = datetime.now()
        
    day_start = datetime.combine(target_date.date(), time(7, 0))
    
    if target_date.time() < time(7, 0):
        day_start = day_start - timedelta(days=1)
        
    day_end = day_start + timedelta(days=1)
    
    return day_start, day_end

def get_yesterday_boundaries():
    """Get the start and end of yesterday (7am to 7am)"""
    yesterday = datetime.now() - timedelta(days=1)
    return get_day_boundaries(yesterday)

@app.route('/')
def index():
    """Main page"""
    return render_template('monitor.html')

@app.route('/api/alarms', methods=['POST'])
def receive_alarm():
    """API to receive alarm data from PLCs (legacy endpoint)"""
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        plc_id = data.get('plc_id', 'unknown')
        
        if 'alarms' in data:
            recorded_alarms = process_alarm_data(plc_id, data['alarms'])
            return jsonify({
                "status": "success", 
                "message": f"Recorded {recorded_alarms} alarm events"
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/today')
def get_today_alarms():
    """Get today's alarms (7am to current time)"""
    try:
        day_start, day_end = get_day_boundaries()
        
        alarms = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= day_start,
            AlarmRecord.timestamp <= datetime.now()
        ).order_by(AlarmRecord.timestamp.desc()).all()
        
        return jsonify({
            "status": "success",
            "day_start": day_start.isoformat(),
            "day_end": day_end.isoformat(),
            "alarms": [alarm.to_dict() for alarm in alarms]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/yesterday')
def get_yesterday_alarms():
    """Get yesterday's alarms (7am to 7am)"""
    try:
        day_start, day_end = get_yesterday_boundaries()
        
        alarms = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= day_start,
            AlarmRecord.timestamp <= day_end
        ).order_by(AlarmRecord.timestamp.desc()).all()
        
        return jsonify({
            "status": "success",
            "day_start": day_start.isoformat(),
            "day_end": day_end.isoformat(),
            "alarms": [alarm.to_dict() for alarm in alarms]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/summary')
def get_alarm_summary():
    """Get alarm summary for today and yesterday"""
    try:
        today_start, today_end = get_day_boundaries()
        yesterday_start, yesterday_end = get_yesterday_boundaries()
        
        plc_id = request.args.get('plc_id', None)
        
        today_query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= today_start,
            AlarmRecord.timestamp <= datetime.now()
        )
        
        yesterday_query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= yesterday_start,
            AlarmRecord.timestamp <= yesterday_end
        )
        
        if plc_id:
            today_query = today_query.filter(AlarmRecord.plc_id == plc_id)
            yesterday_query = yesterday_query.filter(AlarmRecord.plc_id == plc_id)
        
        today_alarms = today_query.all()
        yesterday_alarms = yesterday_query.all()
        
        today_counts = Counter()
        for alarm in today_alarms:
            today_counts[alarm.alarm_code] += 1
        
        yesterday_counts = Counter()
        for alarm in yesterday_alarms:
            yesterday_counts[alarm.alarm_code] += 1
        
        all_codes = set(today_counts.keys()) | set(yesterday_counts.keys())
        
        summary = []
        for code in sorted(all_codes):
            description = ALARM_CODES.get(code, "Unknown alarm")
            
            summary.append({
                "alarm_code": code,
                "description": description,
                "today_count": today_counts.get(code, 0),
                "yesterday_count": yesterday_counts.get(code, 0)
            })
        
        plc_summary = {}
        if not plc_id:  # Only if not already filtered by PLC
            for p_id in PLC_CONFIG.keys():
                p_today_count = AlarmRecord.query.filter(
                    AlarmRecord.timestamp >= today_start,
                    AlarmRecord.timestamp <= datetime.now(),
                    AlarmRecord.plc_id == p_id
                ).count()
                
                p_yesterday_count = AlarmRecord.query.filter(
                    AlarmRecord.timestamp >= yesterday_start,
                    AlarmRecord.timestamp <= yesterday_end,
                    AlarmRecord.plc_id == p_id
                ).count()
                
                plc_summary[p_id] = {
                    "name": PLC_CONFIG[p_id]['name'],
                    "today_count": p_today_count,
                    "yesterday_count": p_yesterday_count
                }
        
        return jsonify({
            "status": "success",
            "today_start": today_start.isoformat(),
            "today_end": today_end.isoformat(),
            "yesterday_start": yesterday_start.isoformat(),
            "yesterday_end": yesterday_end.isoformat(),
            "summary": summary,
            "plc_summary": plc_summary,
            "total_today": len(today_alarms),
            "total_yesterday": len(yesterday_alarms)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/codes')
def get_alarm_codes():
    """Get all alarm codes and descriptions"""
    try:
        return jsonify({
            "status": "success",
            "alarm_codes": ALARM_CODES
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/plcs')
def get_plcs():
    """Get all PLCs"""
    try:
        return jsonify({
            "status": "success",
            "plcs": PLC_CONFIG
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/shift')
def get_shift_alarms():
    """Get alarms for a specific shift (day or night)"""
    try:
        shift_type = request.args.get('type', 'day')  # 'day' or 'night'
        target_date_str = request.args.get('date', None)  # YYYY-MM-DD
        plc_id = request.args.get('plc_id', None)
        
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            target_date = datetime.now()
        
        day_start, _ = get_day_boundaries(target_date)
        
        if shift_type == 'day':
            shift_start = day_start
            shift_end = day_start + timedelta(hours=12)
        else:
            shift_start = day_start + timedelta(hours=12)
            shift_end = day_start + timedelta(hours=24)
        
        query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= shift_start,
            AlarmRecord.timestamp <= shift_end
        )
        
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        alarms = query.order_by(AlarmRecord.timestamp.desc()).all()
        
        alarm_counts = Counter()
        for alarm in alarms:
            alarm_counts[alarm.alarm_code] += 1
        
        summary = []
        for code, count in alarm_counts.most_common():
            description = ALARM_CODES.get(code, "Unknown alarm")
            summary.append({
                "alarm_code": code,
                "description": description,
                "count": count
            })
        
        return jsonify({
            "status": "success",
            "shift_type": shift_type,
            "shift_start": shift_start.isoformat(),
            "shift_end": shift_end.isoformat(),
            "alarms": [alarm.to_dict() for alarm in alarms],
            "summary": summary,
            "total_alarms": len(alarms)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/latest')
def get_latest_alarms():
    """Get the latest N alarms"""
    try:
        limit = int(request.args.get('limit', 10))
        plc_id = request.args.get('plc_id', None)
        
        query = AlarmRecord.query
        
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        alarms = query.order_by(AlarmRecord.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            "status": "success",
            "alarms": [alarm.to_dict() for alarm in alarms],
            "total": len(alarms)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/trend')
def get_alarm_trend():
    """Get alarm trend for the past X hours"""
    try:
        plc_id = request.args.get('plc_id', None)
        hours = int(request.args.get('hours', 24))
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= start_time,
            AlarmRecord.timestamp <= end_time
        )
        
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        trend_data = []
        for hour_offset in range(hours):
            hour_start = end_time - timedelta(hours=hour_offset+1)
            hour_end = end_time - timedelta(hours=hour_offset)
            
            hour_count = query.filter(
                AlarmRecord.timestamp >= hour_start,
                AlarmRecord.timestamp < hour_end
            ).count()
            
            hour_label = hour_start.strftime('%H:00')
            
            trend_data.append({
                "hour": hour_start.hour,
                "hour_label": hour_label,
                "count": hour_count
            })
        
        trend_data.reverse()
        
        return jsonify({
            "status": "success",
            "trend_data": trend_data,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    
    collection_thread = threading.Thread(target=data_collection_loop, daemon=True)
    collection_thread.start()
    logger.info("Started background data collection thread")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
