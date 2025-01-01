import datetime
import json
import os
import re
import logging

# Clean app name by removing version numbers and extensions
def clean_app_name(name):
    """Clean app name by removing version numbers and extensions"""
    # Remove version numbers and extensions
    cleaned_name = re.sub(r'\s*\d+(\.\d+)*\s*', '', name)  
    cleaned_name = re.sub(r'\.(exe|app|dmg|EXE|APP|DMG)$', '', cleaned_name)  
    return cleaned_name.strip()

class TimeEntry:
    """Represents a time entry for an activity."""
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
        self._calculate_duration()

    def _calculate_duration(self):
        # Calculate total duration in seconds
        if isinstance(self.start_time, str):
            self.start_time = datetime.datetime.fromisoformat(self.start_time)
        if isinstance(self.end_time, str):
            self.end_time = datetime.datetime.fromisoformat(self.end_time)
            
        time_diff = self.end_time - self.start_time
        self.duration_seconds = int(time_diff.total_seconds())

    def get_duration_str(self):
        # Return duration as a formatted string
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{seconds}s"

    def serialize(self):
        # Serialize time entry to dictionary
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': self.duration_seconds
        }

    @classmethod
    def from_dict(cls, data):
        # Create TimeEntry from dictionary
        entry = cls(
            start_time=data['start_time'],
            end_time=data['end_time']
        )
        if 'duration_seconds' in data:
            entry.duration_seconds = data['duration_seconds']
        return entry

class Activity:
    """Represents an activity with associated time entries."""
    def __init__(self, name, time_entries, details=None):
        self.name = clean_app_name(name)
        self.time_entries = [TimeEntry(**entry) if isinstance(entry, dict) else entry for entry in time_entries]
        self.details = details or {}
        self._calculate_total_time()

    def _calculate_total_time(self):
        # Calculate total time from time entries
        self.total_seconds = sum(entry.duration_seconds for entry in self.time_entries)
        self.total_time_str = self._format_duration(self.total_seconds)

    def _format_duration(self, seconds):
        # Format duration in hours, minutes, and seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{seconds}s"

    def serialize(self):
        # Serialize activity to dictionary
        return {
            'name': self.name,
            'time_entries': [entry.serialize() for entry in self.time_entries],
            'details': self.details,
            'total_seconds': self.total_seconds,
            'total_time': self.total_time_str
        }

    @classmethod
    def from_dict(cls, data):
        # Create Activity from dictionary
        return cls(
            name=data['name'],
            time_entries=[TimeEntry.from_dict(entry) for entry in data['time_entries']],
            details=data.get('details', {})
        )