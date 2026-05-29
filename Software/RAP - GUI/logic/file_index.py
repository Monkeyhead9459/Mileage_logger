import os
from datetime import datetime
from config import documents_folder

def scan_available_dates(folder=None):
    """Return dict: {year: {month: [days...]}}"""
    if folder is None:
        folder = documents_folder
    file_dates = {}

    for filename in os.listdir(folder):
        if not filename.endswith("_output.csv"):
            continue

        parts = filename.split("_")
        if len(parts) < 4:
            continue

        date_str = parts[3]
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        y, m, d = dt.year, dt.month, dt.day
        file_dates.setdefault(y, {})
        file_dates[y].setdefault(m, [])
        if d not in file_dates[y][m]:
            file_dates[y][m].append(d)

    return file_dates