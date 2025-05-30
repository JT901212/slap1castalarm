from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.expression import extract
from datetime import datetime, time, timedelta
from collections import Counter, defaultdict
import json
import csv
import os

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
    
    # CSVファイルが存在するか確認
    if not os.path.exists(csv_file):
        print(f"Warning: {csv_file} not found, using default alarm definitions")
        # デフォルトの定義を返す
        return {
            "M800": "Base open end OFF",
            "M801": "Side1 open end OFF",
            "M802": "Side2 open end OFF",
            "M803": "Side3 open end OFF",
            "M804": "Side4 open end OFF",
            "M805": "Lower down end OFF",
            "M806": "Upper open end OFF",
            "M807": "Upper-L unlock OFF",
            "M808": "Upper-R unlock OFF",
            "M809": "Lower lock OFF",
            "M810": "Tilt up end OFF",
            "M811": "Cooling mode is wrong",
            "M812": "Side die out of temp",
            "M813": "Pouring interference",
            "M814": "Take out interference",
            "M815": "Ready OFF",
            "M816": "",
            "M817": "MB LS ERROR",
            "M818": "SM1 LS ERROR",
            "M819": "SM2 LS ERROR",
            "M820": "SM3 LS ERROR",
            "M821": "SM4 LS ERROR",
            "M822": "LM LS ERROR",
            "M823": "UM LS ERROR",
            "M824": "UL-L LS ERROR",
            "M825": "UL-R LS ERROR",
            "M826": "LL LS ERROR",
            "M827": "LM Cycle Timeover",
            "M828": "UM Cycle Timeover",
            "M829": "UL Cycle Timeover",
            "M830": "MB Cycle Timeover",
            "M831": "SM1,4 Cycle Timeover",
            "M832": "SM2,3 Cycle Timeover",
            "M833": "LL Cycle Timeover",
            "M834": "UM Thermo CUT",
            "M835": "LM Thermo CUT",
            "M836": "SM Thermo CUT",
            "M837": "",
            "M838": "UM Low Temp",
            "M839": "UM Over Temp",
            "M840": "LM Low Temp",
            "M841": "LM Over Temp",
            "M842": "SM Low Temp",
            "M843": "SM Over Temp",
            "M844": "Pouring COMP Timeover",
            "M845": "Aluminum stuck in hopper",
            "M846": "Aluminum stuck in center",
            "M847": "",
            "M848": "",
            "M849": "",
            "M850": "QD77 Detect error SV1",
            "M851": "QD77 Detect error SV2",
            "M852": "Servo alarm SV1",
            "M853": "Servo alarm SV2",
            "M854": "",
            "M855": "",
            "M856": "",
            "M857": "",
            "M858": "",
            "M859": "",
            "M860": "Center Cooling stuck close",
            "M861": "PCD Cooling stuck close",
            "M862": "Side1L Cooling stuck close",
            "M863": "Side1R Cooling stuck close",
            "M864": "Side2L Cooling stuck close",
            "M865": "Side2R Cooling stuck close",
            "M866": "Upper G Cooling stuck close",
            "M867": "Upper Int Cooling stuck close",
            "M868": "Upper OS Cooling stuck close",
            "M869": "",
            "M870": "Center cooling low flow rate",
            "M871": "PCD cooling low flow rate",
            "M872": "Side1L cooling low flow rate",
            "M873": "Side1R cooling low flow rate",
            "M874": "Side2L cooling low flow rate",
            "M875": "Side2R cooling low flow rate",
            "M876": "",
            "M877": "",
            "M878": "",
            "M879": "",
            "M880": "Center Cooling stuck open",
            "M881": "PCD Cooling stuck open",
            "M882": "Side1L Cooling stuck open",
            "M883": "Side1R Cooling stuck open",
            "M884": "Side2L Cooling stuck open",
            "M885": "Side2R Cooling stuck open",
            "M886": "Upper G Cooling stuck open",
            "M887": "Upper Int Cooling stuck open",
            "M888": "Upper OS Cooling stuck open",
            "M889": "",
            "M890": "",
            "M891": "",
            "M892": "",
            "M893": "",
            "M894": "",
            "M895": "",
            "M896": "",
            "M897": "",
            "M898": "",
            "M899": "",

        }, {f"D{5000+i}": f"M{800+i}" for i in range(100)}, {f"D{5100+i}": f"M{800+i}" for i in range(100)}
    
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                m_code = row.get('m_code')
                description = row.get('description')
                d_code_today = row.get('d_code_today')
                d_code_yesterday = row.get('d_code_yesterday')
                
                if m_code and description:
                    alarm_codes[m_code] = description
                    
                if m_code and d_code_today:
                    d_to_m_today[d_code_today] = m_code
                    
                if m_code and d_code_yesterday:
                    d_to_m_yesterday[d_code_yesterday] = m_code
        
        print(f"Successfully loaded {len(alarm_codes)} alarm definitions from {csv_file}")
        return alarm_codes, d_to_m_today, d_to_m_yesterday
        
    except Exception as e:
        print(f"Error loading alarm definitions: {str(e)}")
        # エラーの場合はデフォルト定義を返す
        return {
            "M800": "Base open end OFF",
            "M801": "Side1 open end OFF",
            "M803": "Side3 open end OFF",
            "M804": "Side4 open end OFF",
            "M805": "Lower down end OFF",
            "M806": "Upper open end OFF",
            "M807": "Upper-L unlock OFF",
            "M808": "Upper-R unlock OFF",
            "M809": "Lower lock OFF",
            "M810": "Tilt up end OFF",
            "M811": "Cooling mode is wrong",
            "M812": "Side die out of temp",
            "M813": "Pouring interference",
            "M814": "Take out interference",
            "M815": "Ready OFF",
            "M816": "",
            "M817": "MB LS ERROR",
            "M818": "SM1 LS ERROR",
            "M819": "SM2 LS ERROR",
            "M820": "SM3 LS ERROR",
            "M821": "SM4 LS ERROR",
            "M822": "LM LS ERROR",
            "M823": "UM LS ERROR",
            "M824": "UL-L LS ERROR",
            "M825": "UL-R LS ERROR",
            "M826": "LL LS ERROR",
            "M827": "LM Cycle Timeover",
            "M828": "UM Cycle Timeover",
            "M829": "UL Cycle Timeover",
            "M830": "MB Cycle Timeover",
            "M831": "SM1,4 Cycle Timeover",
            "M832": "SM2,3 Cycle Timeover",
            "M833": "LL Cycle Timeover",
            "M834": "UM Thermo CUT",
            "M835": "LM Thermo CUT",
            "M836": "SM Thermo CUT",
            "M837": "",
            "M838": "UM Low Temp",
            "M839": "UM Over Temp",
            "M840": "LM Low Temp",
            "M841": "LM Over Temp",
            "M842": "SM Low Temp",
            "M843": "SM Over Temp",
            "M844": "Pouring COMP Timeover",
            "M845": "Aluminum stuck in hopper",
            "M846": "Aluminum stuck in center",
            "M847": "",
            "M848": "",
            "M849": "",
            "M850": "QD77 Detect error SV1",
            "M851": "QD77 Detect error SV2",
            "M852": "Servo alarm SV1",
            "M853": "Servo alarm SV2",
            "M854": "",
            "M855": "",
            "M856": "",
            "M857": "",
            "M858": "",
            "M859": "",
            "M860": "Center Cooling stuck close",
            "M861": "PCD Cooling stuck close",
            "M862": "Side1L Cooling stuck close",
            "M863": "Side1R Cooling stuck close",
            "M864": "Side2L Cooling stuck close",
            "M865": "Side2R Cooling stuck close",
            "M866": "Upper G Cooling stuck close",
            "M867": "Upper Int Cooling stuck close",
            "M868": "Upper OS Cooling stuck close",
            "M869": "",
            "M870": "Center cooling low flow rate",
            "M871": "PCD cooling low flow rate",
            "M872": "Side1L cooling low flow rate",
            "M873": "Side1R cooling low flow rate",
            "M874": "Side2L cooling low flow rate",
            "M875": "Side2R cooling low flow rate",
            "M876": "",
            "M877": "",
            "M878": "",
            "M879": "",
            "M880": "Center Cooling stuck open",
            "M881": "PCD Cooling stuck open",
            "M882": "Side1L Cooling stuck open",
            "M883": "Side1R Cooling stuck open",
            "M884": "Side2L Cooling stuck open",
            "M885": "Side2R Cooling stuck open",
            "M886": "Upper G Cooling stuck open",
            "M887": "Upper Int Cooling stuck open",
            "M888": "Upper OS Cooling stuck open",
            "M889": "",
            "M890": "",
            "M891": "",
            "M892": "",
            "M893": "",
            "M894": "",
            "M895": "",
            "M896": "",
            "M897": "",
            "M898": "",
            "M899": "",
        }, {f"D{5000+i}": f"M{800+i}" for i in range(100)}, {f"D{5100+i}": f"M{800+i}" for i in range(100)}



# Read alarm definitions from CSV
ALARM_CODES, D_TO_M_TODAY, D_TO_M_YESTERDAY = load_alarm_definitions()

## Alarm master data
#ALARM_CODES = {
#    "M800": "Base open end OFF",
#    "M801": "Side1 open end OFF",
#    "M802": "Side2 open end OFF",
#    # ... other alarm codes (same as existing code)
#}

# Mapping from D to M register numbers (today)
# D_TO_M_TODAY = {f"D{5000+i}": f"M{800+i}" for i in range(100)}
# Mapping from D to M register numbers (yesterday)
# D_TO_M_YESTERDAY = {f"D{5100+i}": f"M{800+i}" for i in range(100)}

# PLC configuration
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

# Store the last alarm state to detect changes
# Format: {plc_id: {d_code: value, ...}, ...}
LAST_ALARM_VALUES = {}

# Store the cumulative alarm counts for summary display
# Format: {plc_id: {d_code: count, ...}, ...}
ALARM_COUNTS = defaultdict(lambda: defaultdict(int))

# Alarm data model (with PLC ID and count value)
class AlarmRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    alarm_code = db.Column(db.String(10), nullable=False)
    alarm_description = db.Column(db.String(100), nullable=False)
    plc_id = db.Column(db.String(20), nullable=True)
    plc_name = db.Column(db.String(50), nullable=True)
    count_value = db.Column(db.Integer, default=1)  # The actual count value from PLC
    
    def __repr__(self):
        return f"<Alarm {self.alarm_code} at {self.timestamp} from {self.plc_id} count={self.count_value}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "alarm_code": self.alarm_code,
            "alarm_description": self.alarm_description,
            "plc_id": self.plc_id,
            "plc_name": self.plc_name,
            "count_value": self.count_value
        }

def get_day_boundaries(target_date=None):
    """Calculate day period from 7am to 7am the next day"""
    if target_date is None:
        target_date = datetime.now()
        
    # 7am of the day
    day_start = datetime.combine(target_date.date(), time(7, 0))
    
    # If current time is before 7am, use previous day's 7am
    if target_date.time() < time(7, 0):
        day_start = day_start - timedelta(days=1)
        
    # 7am of the next day
    day_end = day_start + timedelta(days=1)
    
    return day_start, day_end

def get_yesterday_boundaries(target_date=None):
    """Calculate previous day period from 7am to 7am"""
    day_start, day_end = get_day_boundaries(target_date)
    yesterday_start = day_start - timedelta(days=1)
    yesterday_end = day_end - timedelta(days=1)
    
    return yesterday_start, yesterday_end

@app.route('/')
def index():
    """Display main page"""
    return render_template('monitor.html', plc_config=PLC_CONFIG)

@app.route('/api/alarms', methods=['POST'])
def receive_alarm():
    """API to receive alarm data from PLCs"""
    try:
        data = request.json
        
        # データ検証
        if not data:
            return jsonify({"error": "No data received"}), 400
            
        timestamp = datetime.now()
        
        # PLC情報の取得
        plc_id = data.get('plc_id', 'unknown')
        plc_name = data.get('plc_name', 'Unknown PLC')
        
        # このPLCの最後の状態を初期化（存在しない場合）
        if plc_id not in LAST_ALARM_VALUES:
            LAST_ALARM_VALUES[plc_id] = {}
        
        # アラームの記録
        if 'alarms' in data:
            alarms = data['alarms']
            recorded_alarms = 0
            
            for d_code, current_value in alarms.items():
                # 現在の値を整数に変換
                current_value = int(current_value)
                
                # 最後の値を取得（存在しない場合は0）
                last_value = LAST_ALARM_VALUES[plc_id].get(d_code, 0)
                
                # 値が0より大きければ記録（初回起動時）
                if current_value > 0:
                    if d_code in D_TO_M_TODAY:
                        m_code = D_TO_M_TODAY[d_code]
                        description = ALARM_CODES.get(m_code, "Unknown alarm")
                        
                        # 値に変化があったかチェック
                        if current_value != last_value:
                            # 累積カウントを更新
                            ALARM_COUNTS[plc_id][d_code] = current_value
                            
                            # データベースに保存 - 変化ごとに1レコード
                            alarm = AlarmRecord(
                                timestamp=timestamp,
                                alarm_code=m_code,
                                alarm_description=description,
                                plc_id=plc_id,
                                plc_name=plc_name,
                                count_value=current_value  # PLCからの実際のカウント値を保存
                            )
                            db.session.add(alarm)
                            recorded_alarms += 1
                
                # 最後の値を更新
                LAST_ALARM_VALUES[plc_id][d_code] = current_value
                
            db.session.commit()
            return jsonify({
                "status": "success", 
                "message": f"Recorded {recorded_alarms} alarm events"
            }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/today', methods=['GET'])
def get_today_alarms():
    """Get today's alarm list"""
    try:
        day_start, day_end = get_day_boundaries()
        plc_id = request.args.get('plc_id', None)
        
        query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= day_start,
            AlarmRecord.timestamp < day_end
        )
        
        # Filter by specific PLC
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        alarms = query.all()
        
        return jsonify({
            "status": "success", 
            "day_start": day_start.isoformat(),
            "day_end": day_end.isoformat(),
            "alarms": [alarm.to_dict() for alarm in alarms]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/yesterday', methods=['GET'])
def get_yesterday_alarms():
    """Get yesterday's alarm list"""
    try:
        yesterday_start, yesterday_end = get_yesterday_boundaries()
        plc_id = request.args.get('plc_id', None)
        
        query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= yesterday_start,
            AlarmRecord.timestamp < yesterday_end
        )
        
        # Filter by specific PLC
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        alarms = query.all()
        
        return jsonify({
            "status": "success", 
            "day_start": yesterday_start.isoformat(),
            "day_end": yesterday_end.isoformat(),
            "alarms": [alarm.to_dict() for alarm in alarms]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/summary', methods=['GET'])
def get_alarm_summary():
    """Get top 3 alarm occurrences for today and yesterday using PLCからの実数値"""
    try:
        # Today's period
        today_start, today_end = get_day_boundaries()
        
        # Yesterday's period
        yesterday_start, yesterday_end = get_yesterday_boundaries()
        
        # Get PLC ID filter if provided
        plc_id = request.args.get('plc_id', None)
        
        # Get the most recent values for today's alarms by timestamp
        # For each unique alarm code, get the record with the max timestamp in the day range
        today_alarms_query = db.session.query(
            AlarmRecord.alarm_code,
            AlarmRecord.alarm_description,
            AlarmRecord.plc_id,
            AlarmRecord.plc_name,
            db.func.max(AlarmRecord.timestamp).label('max_timestamp')
        ).filter(
            AlarmRecord.timestamp >= today_start,
            AlarmRecord.timestamp < today_end
        ).group_by(
            AlarmRecord.alarm_code, AlarmRecord.plc_id
        )
        
        # Apply PLC filter if provided
        if plc_id:
            today_alarms_query = today_alarms_query.filter(AlarmRecord.plc_id == plc_id)
        
        # Get the latest values for these timestamps
        today_counts = {}
        for record in today_alarms_query.all():
            latest_record = AlarmRecord.query.filter(
                AlarmRecord.alarm_code == record.alarm_code,
                AlarmRecord.plc_id == record.plc_id,
                AlarmRecord.timestamp == record.max_timestamp
            ).first()
            
            if latest_record:
                key = f"{record.alarm_code}_{record.plc_id}"
                today_counts[key] = {
                    "alarm_code": record.alarm_code,
                    "description": record.alarm_description,
                    "plc_id": record.plc_id,
                    "plc_name": record.plc_name,
                    "count": latest_record.count_value
                }
        
        # Same for yesterday
        yesterday_alarms_query = db.session.query(
            AlarmRecord.alarm_code,
            AlarmRecord.alarm_description,
            AlarmRecord.plc_id,
            AlarmRecord.plc_name,
            db.func.max(AlarmRecord.timestamp).label('max_timestamp')
        ).filter(
            AlarmRecord.timestamp >= yesterday_start,
            AlarmRecord.timestamp < yesterday_end
        ).group_by(
            AlarmRecord.alarm_code, AlarmRecord.plc_id
        )
        
        if plc_id:
            yesterday_alarms_query = yesterday_alarms_query.filter(AlarmRecord.plc_id == plc_id)
        
        yesterday_counts = {}
        for record in yesterday_alarms_query.all():
            latest_record = AlarmRecord.query.filter(
                AlarmRecord.alarm_code == record.alarm_code,
                AlarmRecord.plc_id == record.plc_id,
                AlarmRecord.timestamp == record.max_timestamp
            ).first()
            
            if latest_record:
                key = f"{record.alarm_code}_{record.plc_id}"
                yesterday_counts[key] = {
                    "alarm_code": record.alarm_code,
                    "description": record.alarm_description,
                    "plc_id": record.plc_id,
                    "plc_name": record.plc_name,
                    "count": latest_record.count_value
                }
        
        # Convert to list and sort by count
        today_top_alarms = sorted(
            list(today_counts.values()),
            key=lambda x: x['count'],
            reverse=True
        )[:3]
        
        yesterday_top_alarms = sorted(
            list(yesterday_counts.values()),
            key=lambda x: x['count'],
            reverse=True
        )[:3]
        
        # Total counts
        today_total_records = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= today_start,
            AlarmRecord.timestamp < today_end
        )
        
        yesterday_total_records = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= yesterday_start,
            AlarmRecord.timestamp < yesterday_end
        )
        
        if plc_id:
            today_total_records = today_total_records.filter(AlarmRecord.plc_id == plc_id)
            yesterday_total_records = yesterday_total_records.filter(AlarmRecord.plc_id == plc_id)
        
        today_total = today_total_records.count()
        yesterday_total = yesterday_total_records.count()
        
        return jsonify({
            "status": "success",
            "today": {
                "start": today_start.isoformat(),
                "end": today_end.isoformat(),
                "top3": today_top_alarms,
                "total": today_total
            },
            "yesterday": {
                "start": yesterday_start.isoformat(),
                "end": yesterday_end.isoformat(),
                "top3": yesterday_top_alarms,
                "total": yesterday_total
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/codes', methods=['GET'])
def get_alarm_codes():
    """Get a list of alarm codes and descriptions"""
    return jsonify({
        "status": "success",
        "codes": ALARM_CODES
    })

@app.route('/api/plcs', methods=['GET'])
def get_plcs():
    """Get configured PLC list"""
    return jsonify({
        "status": "success",
        "plcs": PLC_CONFIG
    })

@app.route('/api/alarms/summary/<period>')
def get_shift_alarms(period):
    """Get shift-specific alarm summary for the specified period (today or yesterday)"""
    try:
        # Get parameters
        plc_id = request.args.get('plc_id', None)
        start_hour = request.args.get('start_hour', None)
        end_hour = request.args.get('end_hour', None)
        
        # Get date range
        if period == 'today':
            start_date, end_date = get_day_boundaries()
        elif period == 'yesterday':
            start_date, end_date = get_yesterday_boundaries()
        else:
            return jsonify({"error": "Invalid period"}), 400
            
        # Filter by shift time range
        if start_hour and end_hour:
            start_hour = int(start_hour)
            end_hour = int(end_hour)
            
            # Base query
            query = AlarmRecord.query.filter(
                AlarmRecord.timestamp >= start_date,
                AlarmRecord.timestamp < end_date
            )
            
            # Filter by specific PLC
            if plc_id:
                query = query.filter(AlarmRecord.plc_id == plc_id)
            
            # Filter by time range (day shift 7-19 or night shift 19-7)
            if start_hour < end_hour:  # Day shift (e.g., 7:00-19:00)
                query = query.filter(
                    extract('hour', AlarmRecord.timestamp) >= start_hour,
                    extract('hour', AlarmRecord.timestamp) < end_hour
                )
            else:  # Night shift (e.g., 19:00-7:00) - spans two days
                query = query.filter(
                    (extract('hour', AlarmRecord.timestamp) >= start_hour) |
                    (extract('hour', AlarmRecord.timestamp) < end_hour)
                )
        else:
            # If no time range specified, filter by date range only
            query = AlarmRecord.query.filter(
                AlarmRecord.timestamp >= start_date,
                AlarmRecord.timestamp < end_date
            )
            
            if plc_id:
                query = query.filter(AlarmRecord.plc_id == plc_id)
        
        # Get alarms and their latest counts
        alarms = query.all()
        
        # Group by alarm code to get the maximum count value for each alarm code
        alarm_counts = {}
        for alarm in alarms:
            if alarm.alarm_code in alarm_counts:
                # Keep the maximum count value
                alarm_counts[alarm.alarm_code] = max(alarm_counts[alarm.alarm_code], alarm.count_value)
            else:
                alarm_counts[alarm.alarm_code] = alarm.count_value
        
        # Convert to list format
        top_alarms = [
            {"alarm_code": code, "count": count}
            for code, count in alarm_counts.items()
        ]
        
        # Sort by count in descending order
        top_alarms.sort(key=lambda x: x['count'], reverse=True)
        
        # Total count
        total_count = sum(alarm['count'] for alarm in top_alarms)
        
        return jsonify({
            "status": "success",
            "period": period,
            "top_alarms": top_alarms,
            "total_count": total_count
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/latest')
def get_latest_alarms():
    """Get latest alarms"""
    try:
        # Get parameters
        plc_id = request.args.get('plc_id', None)
        limit = int(request.args.get('limit', 10))
        
        # Base query
        query = AlarmRecord.query
        
        # Filter by specific PLC
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        # Get latest alarms
        alarms = query.order_by(AlarmRecord.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            "status": "success",
            "alarms": [alarm.to_dict() for alarm in alarms]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/alarms/trend')
def get_alarm_trend():
    """Get alarm trend for the past X hours"""
    try:
        # Get parameters
        plc_id = request.args.get('plc_id', None)
        hours = int(request.args.get('hours', 24))
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Base query
        query = AlarmRecord.query.filter(
            AlarmRecord.timestamp >= start_time,
            AlarmRecord.timestamp <= end_time
        )
        
        # Filter by specific PLC
        if plc_id:
            query = query.filter(AlarmRecord.plc_id == plc_id)
        
        # Group alarms by hour
        trend_data = []
        for hour_offset in range(hours):
            hour_start = end_time - timedelta(hours=hour_offset+1)
            hour_end = end_time - timedelta(hours=hour_offset)
            
            # Count alarms in this hour range
            hour_count = query.filter(
                AlarmRecord.timestamp >= hour_start,
                AlarmRecord.timestamp < hour_end
            ).count()
            
            # Create hour label
            hour_label = hour_start.strftime('%H:00')
            
            trend_data.append({
                "hour": hour_start.hour,
                "hour_label": hour_label,
                "count": hour_count
            })
        
        # Sort chronologically
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
    app.run(debug=True, host='0.0.0.0', port=5000)