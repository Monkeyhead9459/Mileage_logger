import json
import os
from config import documents_folder

DELETED_FILE = os.path.join(documents_folder, "deleted_journeys.json")

class DeletedJourneys:
    def __init__(self):
        self.data = self.load()

    def load(self):
        if not os.path.exists(DELETED_FILE):
            return {}
        with open(DELETED_FILE, "r") as f:
            return json.load(f)

    def save(self):
        with open(DELETED_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def archive(self, date, journey_ids):
        lst = self.data.setdefault(date, [])
        for jid in journey_ids:
            if jid not in lst:
                lst.append(jid)
        self.save()

    def unarchive(self, date, journey_ids):
        if date not in self.data:
            return
        for jid in journey_ids:
            if jid in self.data[date]:
                self.data[date].remove(jid)
        if not self.data[date]:
            del self.data[date]
        self.save()