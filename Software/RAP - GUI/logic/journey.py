import os
import csv
import requests
from datetime import datetime
from logic.calculate import haversine
from config import documents_folder

def assign_daily_journey_ids(output_folder):
    """
    For every *_output.csv file in the folder:
    - Load rows
    - Sort by timestamp
    - Assign journey_id starting at 1 for that day
    - Save back to the same file
    """

    csv_files = [
        f for f in os.listdir(output_folder)
        if f.endswith("_output.csv")
    ]

    if not csv_files:
        print("No output CSV files found.")
        return

    for filename in csv_files:
        path = os.path.join(output_folder, filename)

        # Load rows
        with open(path, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            continue

        # Check if journey IDs already exist
        if "journey_id" in rows[0] and any(row["journey_id"].strip() for row in rows):
            print(f"Skipping {filename} - already has journey IDs")
            continue

        # Sort by timestamp
        rows.sort(key=lambda r: r["timestamp"])

        # Assign journey IDs starting at 1
        journey_id = 1
        prev = None

        for row in rows:
            if prev is None:
                row["journey_id"] = journey_id
            else:
                # Time difference - handle invalid timestamps
                try:
                    t1 = datetime.fromisoformat(prev["timestamp"])
                    t2 = datetime.fromisoformat(row["timestamp"])
                    time_diff = (t2 - t1).total_seconds() / 60.0
                except ValueError as e:
                    print(f"Warning: Invalid timestamp in {filename}: {e}")
                    # Assign same journey ID for invalid timestamps
                    time_diff = 0

                # Distance difference
                try:
                    dist = haversine(
                        float(prev["latitude"]), float(prev["longitude"]),
                        float(row["latitude"]), float(row["longitude"])
                    )
                except (ValueError, TypeError) as e:
                    print(f"Warning: Invalid coordinates in {filename}: {e}")
                    dist = 0

                # Check conditions
                if dist > 1.0 or time_diff > 5.0:
                    journey_id += 1

                row["journey_id"] = journey_id

            prev = row

        # Write updated file
        fieldnames = list(rows[0].keys())  # preserve all columns

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Updated {filename} with daily journey IDs starting at 1")

    print("✅ Daily journey ID assignment complete.")



def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 18,
        "addressdetails": 1
    }

    headers = {
        "User-Agent": "MileageLoggerApp/1.0"
    }

    r = requests.get(url, params=params, headers=headers)
    data = r.json()

    return data.get("display_name", "Unknown location")

if __name__ == "__main__":
    assign_daily_journey_ids(documents_folder)   