# Progress tracking for project preprocessing
# This module provides a simple in-memory progress tracker for file-by-file updates and activity feed.

from typing import Dict, List
import threading

class ProgressTracker:
    def __init__(self):
        self.progress: Dict[str, Dict] = {}
        self.lock = threading.Lock()

    def start(self, project_id: str, total_files: int):
        with self.lock:
            self.progress[project_id] = {
                'current': 0,
                'total': total_files,
                'stage': 'Started',
                'activity': [],
                'done': False
            }

    def update(self, project_id: str, filename: str, stage: str):
        with self.lock:
            p = self.progress.get(project_id)
            if p:
                p['current'] += 1
                p['stage'] = stage
                p['activity'].append(f"Processing file: {filename} ({p['current']}/{p['total']}) - {stage}")

    def complete(self, project_id: str):
        with self.lock:
            p = self.progress.get(project_id)
            if p:
                p['done'] = True
                p['stage'] = 'Complete'
                p['activity'].append('Preprocessing complete.')

    def get(self, project_id: str):
        with self.lock:
            return self.progress.get(project_id, None)

progress_tracker = ProgressTracker()
