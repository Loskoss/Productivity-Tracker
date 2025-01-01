import psutil
import time
import datetime
import json
import logging
import os
from pathlib import Path
from activity import Activity, TimeEntry, clean_app_name
import win32gui
import win32process

logging.basicConfig(level=logging.INFO)

class Tracker:
    def __init__(self):
        self.activities = []
        self.start_time = datetime.datetime.now()
        self.is_running = False
        self.sessions_dir = Path('sessions')
        self.sessions_dir.mkdir(exist_ok=True)
        self.current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        self.session_file = self.sessions_dir / f"{self.current_date}.json"
        self.current_activity = None
        self.load_activities()
        logging.info('Tracker initialized.')

    def load_activities(self):
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as json_file:
                    data = json.load(json_file)
                    if isinstance(data, dict) and 'activities' in data:
                        for activity_data in data['activities']:
                            activity = Activity.from_dict(activity_data)
                            self.activities.append(activity)
                            logging.info(f"Loaded activity: {activity.name}")
        except FileNotFoundError:
            logging.info('No existing session file found. Starting fresh.')
        except json.JSONDecodeError:
            logging.error('Error reading session file. Starting fresh.')
        except Exception as e:
            logging.error(f'Error loading activities: {str(e)}')

    def get_focused_window_process(self):
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
        cleaned_name = clean_app_name(app_name)

        for activity in self.activities:
            if activity.name == cleaned_name:
                return activity

        new_activity = Activity(cleaned_name, [], app_details)
        self.activities.append(new_activity)
        logging.info(f"Created new activity: {cleaned_name}")
        return new_activity

    def update_activity(self, focused_app):
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
                logging.info(f'Updated activity: {self.current_activity.name}, duration: {time_entry.get_duration_str()}')

            new_activity = self.find_or_create_activity(app_name, app_details)
            self.current_activity = new_activity
            self.current_activity.details = app_details
            self.start_time = current_time

            self.save_activities()

    def save_activities(self):
        try:
            activities_data = [activity.serialize() for activity in self.activities]
            session_data = {
                'date': self.current_date,
                'activities': activities_data
            }

            with open(self.session_file, 'w') as json_file:
                json.dump(session_data, json_file, indent=4, sort_keys=True)
                logging.info(f'Saved activities to {self.session_file}')

        except Exception as e:
            logging.error(f"Error saving activities: {str(e)}")

    def stop_tracking(self):
        if self.current_activity:
            time_entry = TimeEntry(self.start_time, datetime.datetime.now())
            self.current_activity.time_entries.append(time_entry)
            self.current_activity._calculate_total_time()
            self.save_activities()
            logging.info(f'Final update to activity: {self.current_activity.name}')

        self.is_running = False
        logging.info('Stopping activity tracker...')

    def start_tracking(self):
        self.is_running = True
        logging.info('Starting activity tracker...')
        last_focused_app = None

        while self.is_running:
            try:
                focused_app = self.get_focused_window_process()
                if focused_app and (not last_focused_app or \
                                   focused_app['name'] != last_focused_app['name'] or \
                                   focused_app['window_title'] != last_focused_app['window_title']):
                    self.update_activity(focused_app)
                    last_focused_app = focused_app
                time.sleep(1)
            except Exception as e:
                logging.error(f"Error in tracking loop: {str(e)}")
                time.sleep(1)
        logging.info('Activity tracker stopped.')

if __name__ == '__main__':
    tracker = Tracker()
    tracker.start_tracking()