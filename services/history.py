import os
import csv
import json
import shutil
import difflib
from datetime import datetime, timezone
from flask import current_app

class HistoryService:
    def __init__(self):
        # Initialized lazily via current_app
        pass
        
    @property
    def backup_dir(self):
        return current_app.config['BACKUP_DIR']
        
    @property
    def index_path(self):
        return os.path.join(self.backup_dir, 'history.csv')

    def _ensure_dir(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        if not os.path.exists(self.index_path):
            with open(self.index_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'username', 'filename', 'comment', 'backup_path'])

    def save_backup(self, username, comment, source_content=None, source_path=None):
        """
        Save a backup of the current configuration.
        Provide either the content to save, or the path to copy from.
        """
        self._ensure_dir()
        
        timestamp_dt = datetime.now(timezone.utc).astimezone()
        timestamp_str = timestamp_dt.strftime('%Y%m%d_%H%M%S')
        iso_time = timestamp_dt.isoformat()
        
        filename = 'haproxy.cfg' # simplification for MVP
        backup_filename = f"{timestamp_str}_{filename}"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        # Write the backup file
        if source_content is not None:
            with open(backup_path, 'w') as f:
                f.write(source_content)
        elif source_path is not None and os.path.exists(source_path):
            shutil.copy2(source_path, backup_path)
        else:
            raise ValueError("Must provide source_content or valid source_path")
            
        # Append metadata to history.csv
        with open(self.index_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([iso_time, username, filename, comment, backup_path])
            
        return backup_path

    def get_history(self):
        """Read the history metadata CSV and return it as a list of dicts, newest first."""
        self._ensure_dir()
        history = []
        try:
            with open(self.index_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    history.append(row)
            return sorted(history, key=lambda x: x['timestamp'], reverse=True)
        except Exception:
            return []

    def get_backup_content(self, backup_path):
        """Read a specific backup file."""
        # Security check: ensure backup_path is within BACKUP_DIR
        abs_backup_path = os.path.abspath(backup_path)
        abs_backup_dir = os.path.abspath(self.backup_dir)
        
        if not abs_backup_path.startswith(abs_backup_dir):
            raise ValueError("Invalid backup path traversal attempt.")
            
        if not os.path.exists(abs_backup_path):
            return None
            
        with open(abs_backup_path, 'r') as f:
            return f.read()

    def generate_diff(self, current_content, backup_content):
        """Generate a unified diff between two strings using difflib."""
        current_lines = current_content.splitlines(keepends=True)
        backup_lines = backup_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            backup_lines, 
            current_lines, 
            fromfile='Backup Version', 
            tofile='Current Version',
            n=3
        )
        return ''.join(diff)

history_service = HistoryService()
