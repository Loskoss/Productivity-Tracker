from flask import Flask, render_template, jsonify, request
import threading
import os
import json
import atexit
import signal
from autotimer import Tracker
import webbrowser
import logging
import time
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Initialize the Tracker instance
tracker = None
tracking_thread = None
sessions_dir = Path('sessions')
sessions_dir.mkdir(exist_ok=True)

def open_browser():
    """Open browser after a short delay"""
    time.sleep(1.5)  # Wait for Flask to start
    webbrowser.open('http://127.0.0.1:5001')

def signal_handler(signum, frame):
    cleanup()
    os._exit(0)

def initialize_tracker():
    global tracker, tracking_thread
    try:
        # Initialize tracker
        tracker = Tracker()
        
        # Start tracking thread as daemon
        tracking_thread = threading.Thread(target=tracker.start_tracking, daemon=True)
        tracking_thread.start()
        logging.info('Activity tracking started successfully')
    except Exception as e:
        logging.error(f'Failed to initialize tracker: {str(e)}')

def cleanup():
    if tracker:
        logging.info('Shutting down tracker...')
        try:
            tracker.stop_tracking()  # Stop the tracking loop
            tracker.save_activities()
            logging.info('Activities saved successfully')
        except Exception as e:
            logging.error(f'Error saving activities during shutdown: {str(e)}')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/activities', methods=['GET'])
def get_activities():
    try:
        selected_date = datetime.now().strftime('%Y-%m-%d')  # Default to current date
        all_activities = {"date": selected_date, "activities": []}

        if sessions_dir.exists():
            for session_file in sessions_dir.glob('*.json'):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    if session_data.get('date') == selected_date:
                        all_activities["activities"].extend(session_data["activities"])

        logging.info(f"Activities fetched: {json.dumps(all_activities, indent=2)}")
        return jsonify(all_activities)
    except Exception as e:
        logging.error(f"Error reading activities: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/toggle_theme', methods=['POST'])
def toggle_theme():
    return jsonify({'status': 'Theme toggled'})

@app.route('/current_activity', methods=['GET'])
def get_current_activity():
    if tracker.current_activity:
        current_activity = {
            'name': tracker.current_activity.name,
            'details': tracker.current_activity.details,
            'window_title': tracker.current_activity.details.get('window_title', 'Unknown')
        }
        return jsonify(current_activity)
    return jsonify({'name': 'No activity', 'details': {}, 'window_title': ''})

@app.route('/activity/<activity_name>', methods=['GET'])
def get_activity_details(activity_name):
    try:
        selected_date = datetime.now().strftime('%Y-%m-%d')  # Default to current date
        activity_details = None

        if sessions_dir.exists():
            for session_file in sessions_dir.glob('*.json'):
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    if session_data.get('date') == selected_date:
                        for activity in session_data.get('activities', []):
                            if activity.get('name') == activity_name:
                                activity_details = activity
                                break

        if activity_details:
            return jsonify(activity_details)
        else:
            return jsonify({'error': f'Activity {activity_name} not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching activity details for {activity_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Register cleanup functions
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize tracker before running the app
initialize_tracker()

if __name__ == '__main__':
    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        app.run(debug=False, port=5001)  # Set debug to False for production
    except Exception as e:
        logging.error(f'Error starting Flask app: {str(e)}')
        cleanup()
