import csv
import os
from datetime import datetime
from config import documents_folder, filtered_folder
from logic import calculate
from logic.merge_history import MergeHistory


def load_single_day(date, deleted, folder=None):
    """Return list of journey dicts for a single day."""
    if folder is None:
        folder = documents_folder
    filename = f"esp32_device_001_{date}_output.csv"
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return []

    deleted_ids = deleted.data.get(date, [])

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    # Group by journey_id
    grouped = {}
    for r in rows:
        jid = int(r["journey_id"])
        if jid in deleted_ids:
            continue
        grouped.setdefault(jid, [])
        grouped[jid].append(r)

    # Build a lookup from merged_jid → "orig1,orig2" for this date.
    # Only applies to filtered data — raw data is never merged.
    merged_from_lookup = {}
    if os.path.normpath(folder) == os.path.normpath(filtered_folder):
        for entry in MergeHistory().all():
            if entry.get("date") == date:
                orig = entry.get("original_jids", [])
                target = entry.get("merged_jid")
                if target is not None and orig:
                    merged_from_lookup[int(target)] = ",".join(str(j) for j in orig)

    journeys = []
    for jid, pts in grouped.items():
        pts.sort(key=lambda r: r["timestamp"])
        start = pts[0]
        end = pts[-1]

        start_time = start["timestamp"]
        end_time = end["timestamp"]

        try:
            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            duration = str(t2 - t1)
        except ValueError as e:
            print(f"Warning: Invalid timestamp in {filename} (journey {jid}, date {date}): {e}")
            print(f"  Start time: {start_time}")
            print(f"  End time: {end_time}")
            # Skip this journey if timestamps are invalid
            continue

        # Distance + speed (skip segments involving synthetic OSRM bridge points)
        dist = 0
        speeds = []
        for i in range(len(pts) - 1):
            lat1 = float(pts[i]["latitude"])
            lon1 = float(pts[i]["longitude"])
            lat2 = float(pts[i+1]["latitude"])
            lon2 = float(pts[i+1]["longitude"])
            seg_km = calculate.haversine(lat1, lon1, lat2, lon2)
            dist += seg_km
            is_synthetic = (
                pts[i].get("synthetic", "False").strip().lower() == "true" or
                pts[i+1].get("synthetic", "False").strip().lower() == "true"
            )
            if is_synthetic:
                continue
            try:
                ta = datetime.fromisoformat(pts[i]["timestamp"])
                tb = datetime.fromisoformat(pts[i+1]["timestamp"])
                elapsed_h = (tb - ta).total_seconds() / 3600.0
                if elapsed_h > 0:
                    speeds.append(seg_km / elapsed_h)
            except (ValueError, KeyError):
                pass

        max_speed = max(speeds) if speeds else 0.0
        avg_speed = (dist / ((t2 - t1).total_seconds() / 3600.0)) if (t2 - t1).total_seconds() > 0 else 0.0

        journeys.append({
            "journey_id": jid,
            "merged_from": merged_from_lookup.get(jid, ""),
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "distance": dist,
            "max_speed": max_speed,
            "avg_speed": avg_speed,
            "start_lat": float(start["latitude"]),
            "start_lon": float(start["longitude"]),
            "end_lat": float(end["latitude"]),
            "end_lon": float(end["longitude"]),
            "points": pts,
        })

    return journeys


def load_archived_day(date, deleted):
    """Return list of archived journey dicts for a single day."""
    archived_ids = deleted.data.get(date, [])
    if not archived_ids:
        return []

    filename = f"esp32_device_001_{date}_output.csv"
    path = os.path.join(documents_folder, filename)

    if not os.path.exists(path):
        return []

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    grouped = {}
    for r in rows:
        jid = int(r["journey_id"])
        if jid not in archived_ids:
            continue
        grouped.setdefault(jid, [])
        grouped[jid].append(r)

    journeys = []
    for jid, pts in grouped.items():
        pts.sort(key=lambda r: r["timestamp"])
        start = pts[0]
        end = pts[-1]

        start_time = start["timestamp"]
        end_time = end["timestamp"]

        try:
            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            duration = str(t2 - t1)
        except ValueError as e:
            print(f"Warning: Invalid timestamp in {filename} (archived journey {jid}): {e}")
            continue

        dist = 0
        for i in range(len(pts) - 1):
            lat1 = float(pts[i]["latitude"])
            lon1 = float(pts[i]["longitude"])
            lat2 = float(pts[i+1]["latitude"])
            lon2 = float(pts[i+1]["longitude"])
            dist += calculate.haversine(lat1, lon1, lat2, lon2)

        journeys.append({
            "journey_id": jid,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "distance": dist,
            "start_lat": float(start["latitude"]),
            "start_lon": float(start["longitude"]),
            "end_lat": float(end["latitude"]),
            "end_lon": float(end["longitude"]),
        })

    return journeys


def get_coords(date, journey_ids, folder=None):
    """Return coords grouped by journey for map display."""
    if folder is None:
        folder = documents_folder
    filename = f"esp32_device_001_{date}_output.csv"
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return {}

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    coords = {jid: [] for jid in journey_ids}

    for r in rows:
        jid = int(r["journey_id"])
        if jid in coords:
            is_synthetic = r.get("synthetic", "False").strip().lower() == "true"
            coords[jid].append((float(r["latitude"]), float(r["longitude"]), is_synthetic))

    return coords