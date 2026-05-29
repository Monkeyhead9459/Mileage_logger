import os
import csv
from config import documents_folder
from logic.geocode_cache import GeocodeCache
import logic.journey as journey

EXPORT_FOLDER = os.path.join(documents_folder, "selected_journey")

def ensure_export_folder():
    if not os.path.exists(EXPORT_FOLDER):
        os.makedirs(EXPORT_FOLDER)


def export_single_day(rows, settings):
    ensure_export_folder()

    cache = GeocodeCache()

    filename = f"selected_journeys_{rows[0]['_date']}.tsv"
    path = os.path.join(EXPORT_FOLDER, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")

        writer.writerow([
            "Vehicle", "Designation", "Categories",
            "Start Date", "Start Time",
            "End Date", "End Time",
            "Start Zone", "Start Latitude", "Start Longitude",
            "End Zone", "End Latitude", "End Longitude",
            "Distance (km)", "Duration"
        ])

        for r in rows:
            start_dt = r["_start"].split("T")
            end_dt = r["_end"].split("T")

            start_date = start_dt[0]
            start_time = start_dt[1].split("+")[0]

            end_date = end_dt[0]
            end_time = end_dt[1].split("+")[0]

            start_zone = cache.lookup(r["_start_lat"], r["_start_lon"], journey.reverse_geocode)
            end_zone = cache.lookup(r["_end_lat"], r["_end_lon"], journey.reverse_geocode)

            writer.writerow([
                settings["vehicle"],
                settings["designation"],
                settings["categories"],
                start_date,
                start_time,
                end_date,
                end_time,
                start_zone,
                r["_start_lat"],
                r["_start_lon"],
                end_zone,
                r["_end_lat"],
                r["_end_lon"],
                f"{r['_distance']:.2f}",
                r["_duration"]
            ])

    return path