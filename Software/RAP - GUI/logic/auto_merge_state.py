import json
import os
from config import base_path

STATE_FILE = os.path.join(base_path, "auto_merge_state.json")


class AutoMergeState:
    """
    Tracks which filtered CSV files have already been scanned for dropout
    merges, keyed by date string.  Stored value is the file's mtime float at
    the time of processing.  If the mtime matches on the next startup the file
    is skipped; a changed mtime (re-filtered data) triggers a re-scan.
    """

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get_processed_mtime(self, date):
        """Return the stored mtime for *date*, or None if not yet processed."""
        return self._data.get(date)

    def mark_processed(self, date, mtime):
        """Record that *date* was processed when the filtered CSV had *mtime*."""
        self._data[date] = mtime
        self._save()
