import json
import os

STATE_FILE = "state.json"

DEFAULT_STATE = {
    "monitor_folders": [],
    "backup_folder": "",
    "startMonitoring": False
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_STATE.copy()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

