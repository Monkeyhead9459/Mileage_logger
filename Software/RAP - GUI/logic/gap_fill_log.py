import json
import os
from config import filtered_folder

LOG_FILE = os.path.join(filtered_folder, "gap_fill_log.json")


class GapFillLog:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if not os.path.exists(LOG_FILE):
            return {}
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def clear_date(self, date):
        """Remove all log entries for a date (called before re-filtering that date)."""
        if date in self.data:
            del self.data[date]
            self._save()

    def record(self, date, journey_id, gaps_filled, points_added):
        """Upsert a fill record for a specific journey on a date."""
        entries = self.data.setdefault(date, [])
        for entry in entries:
            if entry["journey_id"] == journey_id:
                entry["gaps_filled"] = gaps_filled
                entry["points_added"] = points_added
                self._save()
                return
        entries.append({
            "journey_id": journey_id,
            "gaps_filled": gaps_filled,
            "points_added": points_added,
        })
        self._save()

    def all(self):
        """Return a flat list of {date, journey_id, gaps_filled, points_added} sorted by date."""
        result = []
        for date in sorted(self.data.keys()):
            for entry in self.data[date]:
                result.append({
                    "date": date,
                    "journey_id": entry["journey_id"],
                    "gaps_filled": entry["gaps_filled"],
                    "points_added": entry["points_added"],
                })
        return result
