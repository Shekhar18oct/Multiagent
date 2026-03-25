# Analysis state and pause/resume control (demo implementation)
# This module provides in-memory state and pause/resume for a project analysis.

from typing import Dict
import threading
import time

class AnalysisState:
    def __init__(self):
        self.state: Dict[str, Dict] = {}
        self.lock = threading.Lock()

    def start(self, project_id: str):
        with self.lock:
            self.state[project_id] = {"paused": False, "current_stage": "Started"}

    def pause(self, project_id: str):
        with self.lock:
            if project_id in self.state:
                self.state[project_id]["paused"] = True
                self.state[project_id]["current_stage"] = "Paused"

    def resume(self, project_id: str):
        with self.lock:
            if project_id in self.state:
                self.state[project_id]["paused"] = False
                self.state[project_id]["current_stage"] = "Resumed"

    def get(self, project_id: str):
        with self.lock:
            return self.state.get(project_id, None)

analysis_state = AnalysisState()
