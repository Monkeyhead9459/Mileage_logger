import json
import os
from config import base_path

HISTORY_FILE = os.path.join(base_path, "merge_history.json")


class MergeHistory:
    def __init__(self):
        self._data = self._load()

    def _load(self):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def all(self):
        return list(self._data)

    def add(self, entry):
        """Append a merge record. entry is a dict."""
        self._data.append(entry)
        self._save()

    def remove(self, merge_id):
        """Remove a merge record by its id."""
        self._data = [e for e in self._data if e.get("id") != merge_id]
        self._save()
