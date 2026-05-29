import csv
import os
import shutil
import uuid
import requests
from datetime import datetime, timedelta
from logic.calculate import haversine
from logic.merge_history import MergeHistory
from config import backups_folder, documents_folder, filtered_folder

OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
MAX_BRIDGE_SPEED_KMH = 150.0
RECORDING_INTERVAL_S = 5

DROPOUT_MIN_GAP_KM = 0.1    # end→start gap must be > 100 m to qualify as a dropout
DROPOUT_MAX_GAP_MIN = 10.0  # gap must be < 10 minutes (otherwise it's a new journey)


def get_osrm_route(lat1, lon1, lat2, lon2):
    """Fetch road route from OSRM. Returns list of (lat, lon) or None on failure."""
    url = OSRM_URL.format(lon1=lon1, lat1=lat1, lon2=lon2, lat2=lat2)
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("code") != "Ok":
            return None
        coords = data["routes"][0]["geometry"]["coordinates"]
        return [(lat, lon) for lon, lat in coords]
    except Exception:
        return None


def merge_journeys(date, journey_ids, folder):
    """
    Merge selected journey IDs into one by filling gaps with OSRM road points.
    Only permitted on filtered data. Returns (success: bool, message: str)
    """
    if len(journey_ids) < 2:
        return False, "Select at least 2 journeys to merge"

    if os.path.normpath(folder) == os.path.normpath(documents_folder):
        return False, "Merging is not permitted on raw data — switch to Filtered Data"

    filename = f"esp32_device_001_{date}_output.csv"
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return False, f"File not found: {filename}"

    # Backup original CSV before modifying
    merge_id = str(uuid.uuid4())[:8]
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_name = f"{date}_{ts}_{merge_id}_backup.csv"
    backup_path = os.path.join(backups_folder, backup_name)
    shutil.copy2(path, backup_path)

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        fieldnames = list(reader.fieldnames)

    if "synthetic" not in fieldnames:
        fieldnames.append("synthetic")
    for row in all_rows:
        row.setdefault("synthetic", "False")

    # Separate selected journey rows from the rest
    grouped = {}
    other_rows = []
    for row in all_rows:
        try:
            jid = int(row["journey_id"])
        except (ValueError, KeyError):
            other_rows.append(row)
            continue
        if jid in journey_ids:
            grouped.setdefault(jid, [])
            grouped[jid].append(row)
        else:
            other_rows.append(row)

    if len(grouped) < 2:
        return False, "Could not find all selected journeys in file"

    # Sort selected journeys by their first timestamp
    sorted_jids = sorted(
        grouped.keys(),
        key=lambda jid: grouped[jid][0]["timestamp"] if grouped[jid] else ""
    )

    # Build merged rows, filling each gap via OSRM
    merged_rows = []
    used_osrm = False
    osrm_failed = False

    for i, jid in enumerate(sorted_jids):
        pts = sorted(grouped[jid], key=lambda r: r["timestamp"])
        merged_rows.extend(pts)

        if i < len(sorted_jids) - 1:
            next_jid = sorted_jids[i + 1]
            next_pts = sorted(grouped[next_jid], key=lambda r: r["timestamp"])
            gap_rows = _fill_gap(pts[-1], next_pts[0])
            if gap_rows is None:
                osrm_failed = True
            elif gap_rows:
                merged_rows.extend(gap_rows)
                used_osrm = True

    if not merged_rows:
        return False, "No rows found for selected journeys"

    # Warn if bridging speed is suspiciously high
    _check_bridge_speed(merged_rows)

    # Assign all merged rows to the lowest journey_id
    target_jid = min(journey_ids)
    for row in merged_rows:
        row["journey_id"] = str(target_jid)

    # Combine with other rows and sort by timestamp.
    # Journey IDs are NOT renumbered — the merged journey takes the lowest
    # original ID; all other journeys keep their existing IDs.
    all_new = merged_rows + other_rows
    all_new.sort(key=lambda r: r.get("timestamp", ""))

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_new)

    # Log to merge history
    target_jid = min(journey_ids)
    folder_label = "Filtered" if os.path.normpath(folder) == os.path.normpath(filtered_folder) else "Raw"
    MergeHistory().add({
        "id": merge_id,
        "merge_time": datetime.now().isoformat(timespec="seconds"),
        "date": date,
        "original_jids": sorted_jids,
        "merged_jid": target_jid,
        "folder": folder_label,
        "csv_path": path,
        "backup_path": backup_path,
    })

    if osrm_failed and used_osrm:
        msg = f"Merged {sorted_jids} (some gaps filled via OSRM; some OSRM unavailable — gap points omitted)"
    elif osrm_failed:
        msg = f"Merged {sorted_jids} (OSRM unavailable — gap points omitted)"
    else:
        msg = f"Merged {sorted_jids} via road routing"

    return True, msg


def _fill_gap(last_row, first_row):
    """
    Call OSRM between last_row and first_row.
    Returns list of synthetic CSV rows, [] if gap too small, None if OSRM failed.
    """
    try:
        lat1 = float(last_row["latitude"])
        lon1 = float(last_row["longitude"])
        lat2 = float(first_row["latitude"])
        lon2 = float(first_row["longitude"])
        alt1 = float(last_row.get("altitude", 0))
        alt2 = float(first_row.get("altitude", 0))
        t1 = datetime.fromisoformat(last_row["timestamp"])
        t2 = datetime.fromisoformat(first_row["timestamp"])
    except (ValueError, KeyError):
        return []

    gap_seconds = (t2 - t1).total_seconds()
    if gap_seconds <= RECORDING_INTERVAL_S:
        return []

    road_points = get_osrm_route(lat1, lon1, lat2, lon2)
    if road_points is None:
        return None

    if len(road_points) < 2:
        return []

    steps = max(1, int(gap_seconds / RECORDING_INTERVAL_S)) - 1
    if steps == 0:
        return []

    sampled = _sample_polyline(road_points, steps)
    device = last_row.get("dev_esp32", "esp32_device_001")

    rows = []
    for i, (lat, lon) in enumerate(sampled):
        frac = (i + 1) / (steps + 1)
        ts = t1 + timedelta(seconds=frac * gap_seconds)
        alt = alt1 + frac * (alt2 - alt1)
        rows.append({
            "dev_esp32": device,
            "timestamp": ts.isoformat(),
            "altitude": f"{alt:.1f}",
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "journey_id": last_row.get("journey_id", "1"),
            "synthetic": "True",
        })

    return rows


def _sample_polyline(points, n):
    """Sample n evenly-spaced interior points from a polyline."""
    if n <= 0 or len(points) < 2:
        return []
    if n >= len(points) - 1:
        return points[1:-1]
    indices = [int(round(i * (len(points) - 1) / (n + 1))) for i in range(1, n + 1)]
    return [points[i] for i in indices]


def _check_bridge_speed(rows):
    """Warn if the overall bridging speed exceeds the threshold."""
    try:
        first = rows[0]
        last = rows[-1]
        t1 = datetime.fromisoformat(first["timestamp"])
        t2 = datetime.fromisoformat(last["timestamp"])
        dist = haversine(float(first["latitude"]), float(first["longitude"]),
                         float(last["latitude"]), float(last["longitude"]))
        elapsed_h = (t2 - t1).total_seconds() / 3600
        if elapsed_h > 0 and dist / elapsed_h > MAX_BRIDGE_SPEED_KMH:
            print(f"Warning: Bridging speed {dist/elapsed_h:.0f} km/h exceeds {MAX_BRIDGE_SPEED_KMH} km/h — verify this is a real dropout")
    except Exception:
        pass


def _renumber_journeys(rows):
    """Renumber journey_ids sequentially starting at 1, preserving order."""
    old_to_new = {}
    counter = 1
    for row in rows:
        try:
            jid = int(row["journey_id"])
        except (ValueError, KeyError):
            continue
        if jid not in old_to_new:
            old_to_new[jid] = counter
            counter += 1
    for row in rows:
        try:
            jid = int(row["journey_id"])
            row["journey_id"] = str(old_to_new[jid])
        except (ValueError, KeyError):
            pass
    return rows


def find_dropout_chains(date, folder):
    """
    Scan the filtered CSV for *date* and return a list of journey-ID chains
    that qualify as GPS dropouts.

    A pair (J_n, J_{n+1}) qualifies when:
      - the gap between J_n's last point and J_{n+1}'s first point is
        > DROPOUT_MIN_GAP_KM (100 m)  — real movement, not same-spot noise
      - the time difference is < DROPOUT_MAX_GAP_MIN (10 min) — dropout, not
        a new trip

    Consecutive qualifying pairs are chained together, e.g. [[2, 3], [5, 6, 7]].
    """
    filename = f"esp32_device_001_{date}_output.csv"
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return []

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return []

    grouped = {}
    for row in rows:
        try:
            jid = int(row["journey_id"])
        except (ValueError, KeyError):
            continue
        grouped.setdefault(jid, [])
        grouped[jid].append(row)

    journey_data = []
    for jid, pts in grouped.items():
        pts.sort(key=lambda r: r["timestamp"])
        journey_data.append((jid, pts))
    journey_data.sort(key=lambda x: x[1][0]["timestamp"])

    n = len(journey_data)
    pair_qualifies = []
    for i in range(n - 1):
        _, pts_a = journey_data[i]
        _, pts_b = journey_data[i + 1]
        try:
            dist_km = haversine(
                float(pts_a[-1]["latitude"]), float(pts_a[-1]["longitude"]),
                float(pts_b[0]["latitude"]),  float(pts_b[0]["longitude"])
            )
            t_end   = datetime.fromisoformat(pts_a[-1]["timestamp"])
            t_start = datetime.fromisoformat(pts_b[0]["timestamp"])
            gap_min = (t_start - t_end).total_seconds() / 60.0
        except (ValueError, KeyError):
            pair_qualifies.append(False)
            continue
        pair_qualifies.append(
            dist_km > DROPOUT_MIN_GAP_KM and 0 <= gap_min < DROPOUT_MAX_GAP_MIN
        )

    chains = []
    i = 0
    while i < n:
        if i < n - 1 and pair_qualifies[i]:
            chain = [journey_data[i][0], journey_data[i + 1][0]]
            j = i + 1
            while j < n - 1 and pair_qualifies[j]:
                chain.append(journey_data[j + 1][0])
                j += 1
            chains.append(chain)
            i = j + 1
        else:
            i += 1

    return chains


def run_auto_merge(filtered_folder_path):
    """
    Scan every filtered CSV for GPS dropouts and auto-merge qualifying chains.

    Uses AutoMergeState to skip dates whose filtered CSV has not changed since
    the last run — so on typical startups almost no files are re-processed.
    """
    from logic.auto_merge_state import AutoMergeState
    state = AutoMergeState()

    try:
        csv_files = [f for f in os.listdir(filtered_folder_path) if f.endswith("_output.csv")]
    except OSError:
        return

    for filename in csv_files:
        parts = filename.replace("_output.csv", "").split("_")
        date = parts[-1]

        path = os.path.join(filtered_folder_path, filename)
        try:
            current_mtime = os.path.getmtime(path)
        except OSError:
            continue

        stored = state.get_processed_mtime(date)
        if stored is not None and abs(current_mtime - stored) < 0.1:
            continue

        # Re-find chains after each merge (IDs shift due to renumbering)
        while True:
            chains = find_dropout_chains(date, filtered_folder_path)
            if not chains:
                break
            ok, msg = merge_journeys(date, chains[0], filtered_folder_path)
            if ok:
                print(f"Auto-merge {date}: {msg}")
            else:
                print(f"Auto-merge {date} skipped: {msg}")
                break

        try:
            new_mtime = os.path.getmtime(path)
        except OSError:
            new_mtime = current_mtime
        state.mark_processed(date, new_mtime)
