/**
 * monitor.js - JavaScript for the alarm monitor display
 * Shows day and night shift alarm data for machines 1A and 1B
 */

// Interval ID for real-time update
let updateInterval;
// Data cache
let alarmDataCache = {
    today: [],
    yesterday: []
};

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    startRealTimeUpdates();
});

/**
 * Initialize the page
 */
function initializePage() {
    updateCurrentTime();
    loadAlarmCodes();
    updateDashboard();

    // Update current time every minute
    setInterval(updateCurrentTime, 60000);
}

/**
 * Start real-time updates
 */
function startRealTimeUpdates() {
    // Update data every 30 seconds
    updateInterval = setInterval(updateDashboard, 30000);
}

/**
 * Update current time display
 */
function updateCurrentTime() {
    const now = new Date();
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    document.getElementById('current-time').textContent = now.toLocaleString('ja-JP', options);
}

/**
 * Load alarm code definitions
 */
function loadAlarmCodes() {
    fetch('/api/alarms/codes')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Cache alarm codes
                window.ALARM_CODES = data.codes;
            }
        })
        .catch(error => {
            console.error('Failed to load alarm codes:', error);
        });
}

/**
 * Update dashboard data
 */
function updateDashboard() {
    // Update last updated time
    const now = new Date();
    document.getElementById('last-updated').textContent = now.toLocaleString('ja-JP');

    // Update shift date labels
    updateShiftDateLabels();
    
    // Update day shift alarms for both machines
    fetchShiftAlarms('day', '1A');
    fetchShiftAlarms('day', '1B');
    
    // Update night shift alarms for both machines
    fetchShiftAlarms('night', '1A');
    fetchShiftAlarms('night', '1B');
}

/**
 * Update date labels for shift displays
 */
function updateShiftDateLabels() {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    // Format dates
    const options = { month: '2-digit', day: '2-digit' };
    const todayStr = today.toLocaleDateString('ja-JP', options);
    
    document.getElementById('day-shift-date').textContent = `${todayStr}`;
    document.getElementById('night-shift-date').textContent = `${todayStr}`;
}

/**
 * Fetch and display alarm data for the specified shift and machine
 * @param {string} shift - Shift type ('day' or 'night')
 * @param {string} plcId - PLC ID ('1A' or '1B')
 */
function fetchShiftAlarms(shift, plcId) {
    // Calculate time range for shift (7:00-19:00 or 19:00-7:00)
    const timeRangeParam = calculateShiftTimeRange(shift);
    
    // Today's data
    const todayParams = new URLSearchParams({
        start_hour: timeRangeParam.start_hour,
        end_hour: timeRangeParam.end_hour,
        plc_id: plcId
    });
    
    // Fetch today's data for this machine and shift
    fetch(`/api/alarms/summary/today?${todayParams}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Save data to cache
                alarmDataCache[`today_${shift}_${plcId}`] = data;
                
                // Display data in table
                displayAlarmTable(`today-${shift}-alarms-${plcId}`, data.top_alarms);
                
                // Display total count
                document.getElementById(`today-${shift}-total-${plcId}`).textContent = 
                    `Total: ${data.total_count}`;
            }
        })
        .catch(error => {
            console.error(`Failed to fetch ${shift} shift alarm data for ${plcId}:`, error);
        });
    
    // Yesterday's data
    const yesterdayParams = new URLSearchParams({
        start_hour: timeRangeParam.start_hour,
        end_hour: timeRangeParam.end_hour,
        plc_id: plcId
    });
    
    // Fetch yesterday's data for this machine and shift
    fetch(`/api/alarms/summary/yesterday?${yesterdayParams}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Save data to cache
                alarmDataCache[`yesterday_${shift}_${plcId}`] = data;
                
                // Display data in table
                displayAlarmTable(`yesterday-${shift}-alarms-${plcId}`, data.top_alarms);
                
                // Display total count
                document.getElementById(`yesterday-${shift}-total-${plcId}`).textContent = 
                    `Total: ${data.total_count}`;
            }
        })
        .catch(error => {
            console.error(`Failed to fetch yesterday's ${shift} shift alarm data for ${plcId}:`, error);
        });
}

/**
 * Calculate time range for shift
 * @param {string} shift - Shift type ('day' or 'night')
 * @returns {Object} Time range parameters
 */
function calculateShiftTimeRange(shift) {
    if (shift === 'day') {
        // Day shift: 07:00-19:00
        return {
            start_hour: 7,
            end_hour: 19
        };
    } else {
        // Night shift: 19:00-07:00
        return {
            start_hour: 19,
            end_hour: 7
        };
    }
}

/**
 * Display alarm data in table
 * @param {string} tableId - Table ID
 * @param {Array} alarms - Array of alarm data
 */
function displayAlarmTable(tableId, alarms) {
    const tableBody = document.querySelector(`#${tableId} tbody`);
    tableBody.innerHTML = '';
    
    if (!alarms || alarms.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" style="text-align: center;">No alarm data</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Display top 3 alarms
    alarms.slice(0, 3).forEach((alarm, index) => {
        const row = document.createElement('tr');
        
        // Get alarm description from global ALARM_CODES object
        const description = window.ALARM_CODES && window.ALARM_CODES[alarm.alarm_code] 
            ? window.ALARM_CODES[alarm.alarm_code] 
            : 'Unknown';
        
        row.innerHTML = `
            <td>${index + 1}</td>
            <td>${alarm.alarm_code}</td>
            <td>${description}</td>
            <td>${alarm.count}</td>
        `;
        
        // Apply special style to top alarm
        if (index === 0) {
            row.classList.add('status-critical');
        }
        
        tableBody.appendChild(row);
    });
}