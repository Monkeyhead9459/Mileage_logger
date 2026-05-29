import json
import os
from config import documents_folder

CACHE_FILE = os.path.join(documents_folder, "geocode_cache.json")


class GeocodeCache:
    def __init__(self):
        self.cache = self._load()

    def _load(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self):
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self.cache, f, indent=2)
        except OSError:
            pass

    def lookup(self, lat, lon, resolver):
        key = f"{round(lat, 6)},{round(lon, 6)}"
        if key in self.cache:
            return self.cache[key]

        value = resolver(lat, lon)
        self.cache[key] = value
        self._save()
        return value