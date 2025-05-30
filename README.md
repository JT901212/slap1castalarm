# SLAP1 Casting Alarm Monitor

PLC alarm monitoring system that integrates with PLC Monitor Master service.

## Components
- `app.py`: Main Flask application for alarm monitoring
- `plc_connection.py`: PLC data collection service (to be integrated)
- `plc_monitor_master.py`: Reference master service (runs on port 8000)

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Start master service: `python plc_monitor_master.py` (port 8000)
3. Start alarm monitor: `python app.py` (port 5000)

## Integration Task
Integrate `plc_connection.py` functionality into `app.py` and change from direct PLC connection to HTTP API calls to the master service.
