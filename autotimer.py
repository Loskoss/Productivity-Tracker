"""This module tracks user activities and logs them into sessions using JSON files."""

import psutil  
import datetime 
import time  
import json  
import logging  
from pathlib import Path  
from activity import Activity, TimeEntry, clean_app_name  # Custom classes
import win32gui  # Windows GUI
import win32process  # Windows processes
import threading

logging.basicConfig(level=logging.INFO)  # Logging configuration

class Tracker:
    """Tracks user activities and manages sessions."""
    def __init__(self):
        """Initializes the Tracker and loads activities."""
        self.activities = []  # Activities list
        self.start_time = datetime.datetime.now()  
        self.is_running = False  # Tracking status
        self.sessions_dir = Path('sessions')  # Session directory
        self.sessions_dir.mkdir(parents=True, exist_ok=True)  # Create if not exists
        self.current_date = datetime.datetime.now().strftime('%Y-%m-%d')  
        self.session_file = self.sessions_dir / f"{self.current_date}.json"  # Session file path
        self.current_activity = None  # Current activity
        self.load_activities()  
        logging.info('Tracker initialized.')  # Log initialization

    def load_activities(self):
        """Loads activities from the session file."""
        try:
            if self.session_file.exists():
                logging.debug(f"Loading session file: {self.session_file}")
                with open(self.session_file, 'r') as json_file:
                    data = json.load(json_file)  
                    if 'activities' in data:
                        for activity_data in data['activities']:
                            activity = Activity.from_dict(activity_data)  
                            self.activities.append(activity)  
                            logging.debug(f"Loaded activity: {activity.name}")  
        except FileNotFoundError:
            logging.info('No existing session file found.')  
        except json.JSONDecodeError:
            logging.error('Error reading session file.')  
        except Exception as e:
            logging.error(f'An unexpected error occurred: {e}')  

    def get_focused_window_process(self):
        """Gets the process details of the currently focused window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            window_title = win32gui.GetWindowText(hwnd)

            if not window_title:
                window_title = process.name()
            elif window_title == "Untitled":
                window_title = f"{process.name()} - {window_title}"

            return {
                'exe': process.exe(),
                'name': process.name(),
                'window_title': window_title
            }
        except Exception as e:
            logging.error(f"Error getting focused window: {str(e)}")
            return None

    def find_or_create_activity(self, app_name, app_details):
        """Finds an existing activity or creates a new one based on the app name."""
        cleaned_name = clean_app_name(app_name)

        for activity in self.activities:
            if activity.name == cleaned_name:
                return activity

        new_activity = Activity(cleaned_name, [], app_details)
        self.activities.append(new_activity)
        logging.debug(f"Created new activity: {cleaned_name}")
        return new_activity

    def update_activity(self, focused_app):
        """Updates the current activity based on the focused app."""
        if focused_app:
            current_time = datetime.datetime.now()
            app_name = focused_app['name']
            app_details = {
                'exe': focused_app['exe'],
                'window_title': focused_app['window_title']
            }
            if self.current_activity:
                time_entry = TimeEntry(self.start_time, current_time)
                self.current_activity.time_entries.append(time_entry)
                self.current_activity._calculate_total_time()
                logging.debug(f'Updated activity: {self.current_activity.name}, duration: {time_entry.get_duration_str()}')
            new_activity = self.find_or_create_activity(app_name, app_details)
            self.current_activity = new_activity
            self.current_activity.details = app_details
            self.start_time = current_time
            self.save_activities()

    def save_activities(self):
        """Saves the current activities to the session file."""
        try:
            activities_data = [activity.serialize() for activity in self.activities]  
            session_data = {'activities': activities_data}  
            with open(self.session_file, 'w') as json_file:
                json.dump(session_data, json_file, indent=2)  
        except Exception as e:
            logging.error(f'Error saving activities: {str(e)}')  

    def focus_change_listener(self):
        """Listens for changes in the foreground window and updates activities."""
        self.is_running = True
        last_focused_window = None
        while self.is_running:
            focused_window = self.get_focused_window_process()
            if focused_window != last_focused_window:
                self.update_activity(focused_window)
                last_focused_window = focused_window
            time.sleep(0.1)  # Small delay to prevent excessive CPU usage

    def stop_tracking(self):
        """Stops the tracking process and saves the session data."""
        self.is_running = False
        duration = datetime.datetime.now() - self.start_time
        logging.info(f'Tracking stopped. Duration: {duration}')
        self.save_activities()

    def save_session(self):
        """Saves the current activities to the session file."""
        try:
            with open(self.session_file, 'w') as json_file:
                json.dump({'activities': [activity.to_dict() for activity in self.activities]}, json_file)
                logging.info('Session saved successfully.')
        except Exception as e:
            logging.error(f'Error saving session: {e}')

if __name__ == '__main__':
    tracker = Tracker()
    listener_thread = threading.Thread(target=tracker.focus_change_listener, daemon=True)
    listener_thread.start()
    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        tracker.stop_tracking()
