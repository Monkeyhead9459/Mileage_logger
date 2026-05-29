import json
import os
from config import documents_folder

SETTINGS_FILE = os.path.join(documents_folder, "settings.json")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"vehicle": "", "designation": "", "categories": ""}

    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)