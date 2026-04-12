from config import APP_VERSION
import os
import sys
import json
import time
import requests
import subprocess

# IMPORTANT: Use the RAW GitHub URL, not the "tree" URL
LATEST_JSON_URL = "https://raw.githubusercontent.com/Monkeyhead9459/Mileage_logger/main/Software/RAP%20-%20GUI/app-data/latest.json"


def get_local_version():
    """Return the version hardcoded in the EXE."""
    return APP_VERSION


def get_latest_info():
    """Fetch latest version info from GitHub."""
    r = requests.get(LATEST_JSON_URL, timeout=5)
    return r.json()


def download_update(download_url, target_path):
    """Download the new EXE."""
    r = requests.get(download_url, stream=True)
    with open(target_path, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            f.write(chunk)


def apply_update(new_exe_path):
    """Replace the running EXE using a temporary batch file."""
    current_exe = sys.argv[0]
    bat_path = new_exe_path + ".bat"

    with open(bat_path, "w") as bat:
        bat.write(f"""
@echo off
timeout /t 1 >nul
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")

    subprocess.Popen([bat_path], shell=True)
    sys.exit()


def auto_update():
    """Main silent update routine."""
    try:
        local = get_local_version()
        latest = get_latest_info()

        if latest["version"] != local:
            update_url = latest["url"]
            update_path = os.path.join(os.path.dirname(sys.argv[0]), "update.exe")

            download_update(update_url, update_path)
            apply_update(update_path)

    except Exception:
        # Silent fail — do not interrupt the app
        pass