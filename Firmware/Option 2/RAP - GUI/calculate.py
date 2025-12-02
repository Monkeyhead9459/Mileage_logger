import os
import csv
import math
from datetime import datetime
from collections import defaultdict
from config import documents_folder 

# --- Haversine Formula ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# --- Load coordinates from a CSV file ---
def getCoords(date_str, device):
    csv_filename = f"{device}_{date_str}_output.csv"
    csv_path = os.path.join(documents_folder, csv_filename)

    if not os.path.isfile(csv_path):
        return []

    coords = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get("latitude", 0))
                lon = float(row.get("longitude", 0))
                coords.append((lat, lon))
            except ValueError:
                continue
    return coords


# --- Calculate mileage for a single day ---
def mileageDay(date_str=str, device="esp32_device_001"):
    coords = getCoords(date_str, device)
    if len(coords) < 2:
        return 0.0, f"No valid GPS data for {date_str}"

    total_km = 0.0
    for i in range(1, len(coords)):
        total_km += haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])

    return total_km, f"Processed {len(coords)} GPS points"


# --- Helper: total mileage for a period (month/year) ---
def calculate_total_mileage_for_period(device, year=None, month=None):
    total_km = 0.0
    total_points = 0

    for filename in os.listdir(documents_folder):
        if not filename.startswith(device) or not filename.endswith("_output.csv"):
            continue

        # Extract date part safely
        try:
            date_part = filename.split("_")[3]  # e.g. device_2025-10-05_output.csv
            file_date = datetime.strptime(date_part, "%Y-%m-%d")
        except (IndexError, ValueError):
            continue

        if year and file_date.year != year:
            continue
        if month and file_date.month != month:
            continue

        coords = getCoords(file_date.strftime("%Y-%m-%d"), device)
        if len(coords) < 2:
            continue

        for i in range(1, len(coords)):
            total_km += haversine(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
            total_points += 1

    return total_km, total_points


# --- Monthly mileage ---
def mileageMonth(month_name, year_str, device="esp32_device_001"):
    if not month_name or not year_str:
        return 0.0, "Month and year are required"

    try:
        month_num = datetime.strptime(month_name, "%B").month
        year_num = int(year_str)
    except ValueError:
        return 0.0, "Invalid month or year"

    total_km, total_points = calculate_total_mileage_for_period(device, year=year_num, month=month_num)
    if total_points == 0:
        return 0.0, f"No data found for {month_name} {year_num}"

    return total_km, f"Processed {total_points} GPS points"


# --- Yearly mileage ---
def mileageYear(year_str, device="esp32_device_001"):
    if not year_str:
        return 0.0, "Year is required"

    try:
        year_num = int(year_str)
    except ValueError:
        return 0.0, "Invalid year"

    total_km, total_points = calculate_total_mileage_for_period(device, year=year_num)
    if total_points == 0:
        return 0.0, f"No data found for {year_num}"

    return total_km, f"Processed {total_points} GPS points"
