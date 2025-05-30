import pymcprotocol
import time
import requests
from datetime import datetime
import logging

# ログの設定（英語メッセージに変更）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("plc_connection.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PLC_Connection")

# Flask server configuration
SERVER_URL = 'http://localhost:5000/api/alarms'

# PLC configuration
PLC_CONFIG = {
    '1A': {
        'ip': '192.168.150.22',
        'port': 5020,  # For Q series use 5007, for iQ-R series use 5002
        'name': 'Casting_1A'
    },
    '1B': {
        'ip': '192.168.150.24',
        'port': 5020,  # For Q series use 5007, for iQ-R series use 5002
        'name': 'Casting_1B'
    }
}

def read_plc_data(plc_id):
    """Read D5000-D5099 data from PLC"""
    plc_info = PLC_CONFIG.get(plc_id)
    if not plc_info:
        logger.error(f"Unknown PLC ID: {plc_id}")
        return None
    
    try:
        # Connect to PLC using pymcprotocol
        pymc = pymcprotocol.Type3E()
        pymc.connect(plc_info['ip'], plc_info['port'])
        
        # Read 100 registers starting from D5000
        # Note: We're using just 2 arguments as per the API specification
        word_values = pymc.batchread_wordunits("D5000", 100)
        
        # Close the connection
        pymc.close()
        
        # Store results in a dictionary
        alarm_data = {}
        for i in range(100):
            d_code = f"D{5000 + i}"
            alarm_data[d_code] = word_values[i]
        
        logger.info(f"Successfully read data from PLC {plc_id}: {len(alarm_data)} registers")
        return alarm_data
        
    except Exception as e:
        logger.error(f"Error reading data from PLC {plc_id}: {str(e)}")
        return None

def send_alarm_data_to_server(plc_id, alarm_data):
    """Send alarm data to Flask server"""
    if not alarm_data:
        return False
    
    payload = {
        "alarms": alarm_data,
        "timestamp": datetime.now().isoformat(),
        "plc_id": plc_id,
        "plc_name": PLC_CONFIG[plc_id]['name']
    }
    
    try:
        response = requests.post(SERVER_URL, json=payload)
        if response.status_code == 201:
            logger.info(f"Successfully sent PLC {plc_id} data to server")
            return True
        else:
            logger.error(f"Server response error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending data to server: {str(e)}")
    
    return False

def main():
    """Main processing loop"""
    logger.info("Starting PLC data collection program")
    
    try:
        # Initial data collection and transmission at startup
        for plc_id in PLC_CONFIG.keys():
            logger.info(f"Initial data collection from PLC {plc_id}")
            alarm_data = read_plc_data(plc_id)
            if alarm_data:
                send_alarm_data_to_server(plc_id, alarm_data)
        
        # Regular data collection loop
        while True:
            for plc_id in PLC_CONFIG.keys():
                alarm_data = read_plc_data(plc_id)
                if alarm_data:
                    send_alarm_data_to_server(plc_id, alarm_data)
            
            # Run every 10 seconds
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Program terminated")

if __name__ == "__main__":
    # Check if pymcprotocol is installed
    try:
        import pymcprotocol
    except ImportError:
        logger.error("pymcprotocol is not installed. Install it with the command:")
        logger.error("pip install pymcprotocol")
        exit(1)
    
    main()