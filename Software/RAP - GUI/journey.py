import os
import csv
from datetime import datetime
from calculate import haversine
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

        # Sort by timestamp
        rows.sort(key=lambda r: r["timestamp"])

        # Assign journey IDs starting at 1
        journey_id = 1
        prev = None

        for row in rows:
            if prev is None:
                row["journey_id"] = journey_id
            else:
                # Time difference
                t1 = datetime.fromisoformat(prev["timestamp"])
                t2 = datetime.fromisoformat(row["timestamp"])
                time_diff = (t2 - t1).total_seconds() / 60.0

                # Distance difference
                dist = haversine(
                    float(prev["latitude"]), float(prev["longitude"]),
                    float(row["latitude"]), float(row["longitude"])
                )

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

assign_daily_journey_ids(documents_folder)   