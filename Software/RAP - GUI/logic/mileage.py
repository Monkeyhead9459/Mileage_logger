import os
from datetime import datetime
from config import documents_folder
from logic import journey_loader


def mileage_month(month_name, year, deleted, folder=None):
    if folder is None:
        folder = documents_folder
    month_num = datetime.strptime(month_name, "%B").month
    total = 0.0
    msg = f"Mileage for {month_name} {year}:"

    for filename in os.listdir(folder):
        if not filename.endswith("_output.csv"):
            continue

        parts = filename.split("_")
        if len(parts) < 4:
            continue

        try:
            dt = datetime.strptime(parts[3], "%Y-%m-%d")
        except ValueError:
            continue

        if dt.year == int(year) and dt.month == month_num:
            date_str = dt.strftime("%Y-%m-%d")
            journeys = journey_loader.load_single_day(date_str, deleted, folder=folder)
            total += sum(j["distance"] for j in journeys)

    return total, msg


def mileage_year(year, deleted, folder=None):
    if folder is None:
        folder = documents_folder
    total = 0.0
    msg = f"Mileage for {year}:"

    for filename in os.listdir(folder):
        if not filename.endswith("_output.csv"):
            continue

        parts = filename.split("_")
        if len(parts) < 4:
            continue

        try:
            dt = datetime.strptime(parts[3], "%Y-%m-%d")
        except ValueError:
            continue

        if dt.year == int(year):
            date_str = dt.strftime("%Y-%m-%d")
            journeys = journey_loader.load_single_day(date_str, deleted, folder=folder)
            total += sum(j["distance"] for j in journeys)

    return total, msg