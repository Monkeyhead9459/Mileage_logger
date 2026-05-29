import csv
import json
import os
import re
import requests
from datetime import datetime, timedelta
from logic.calculate import haversine
from config import base_path


STATE_FILE = os.path.join(base_path, "gap_fill_state.json")


class GapFillState:
    """Tracks filtered CSV mtimes to avoid re-running gap-fill on unchanged files."""

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def needs_processing(self, path):
        if not os.path.exists(path):
            return False
        return self._data.get(path, 0) < os.path.getmtime(path)

    def mark_processed(self, path):
        self._data[path] = os.path.getmtime(path)
        self._save()

ROAD_FILL_MIN_KM = 0.03     # 30 m — fill between pairs further apart than this
OSRM_WAYPOINT_LIMIT = 50    # max waypoints per OSRM request (public server cap)

OSRM_MULTI_URL = (
    "https://router.project-osrm.org/route/v1/driving/{coords}"
    "?overview=false&geometries=geojson&steps=true"
)


# ----------------------------------------------------------------
# OSRM helpers
# ----------------------------------------------------------------

def _get_leg_geometries(coords):
    """
    Single OSRM call with multiple waypoints.
    Returns a list of per-leg point lists [(lat, lon), ...], or None on failure.
    """
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in coords)
    url = OSRM_MULTI_URL.format(coords=coord_str)
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if data.get("code") != "Ok":
            return None
        legs = data["routes"][0]["legs"]
        result = []
        for leg in legs:
            leg_pts = []
            for step in leg.get("steps", []):
                for lon, lat in step["geometry"]["coordinates"]:
                    pt = (lat, lon)
                    if not leg_pts or pt != leg_pts[-1]:
                        leg_pts.append(pt)
            result.append(leg_pts)
        return result
    except Exception:
        return None


def _get_all_legs(all_coords):
    """
    Fetch leg geometries for an entire journey, chunking into batches of
    OSRM_WAYPOINT_LIMIT if necessary.
    Returns list of per-leg point lists, or None if any OSRM request fails.
    """
    if len(all_coords) < 2:
        return []
    if len(all_coords) <= OSRM_WAYPOINT_LIMIT:
        return _get_leg_geometries(all_coords)

    # Chunk with one-point overlap so legs connect cleanly
    all_legs = []
    i = 0
    while i < len(all_coords) - 1:
        chunk = all_coords[i: i + OSRM_WAYPOINT_LIMIT]
        legs = _get_leg_geometries(chunk)
        if legs is None:
            return None
        all_legs.extend(legs)
        i += OSRM_WAYPOINT_LIMIT - 1

    return all_legs


# ----------------------------------------------------------------
# Public API
# ----------------------------------------------------------------


def run_gap_fill(folder):
    """
    Post-merge step: scan all filtered CSVs in *folder* and apply within-journey
    road gap-filling.  Uses mtime-based caching so unchanged files are skipped.
    Runs AFTER run_auto_merge() so merged journeys are processed as one unit,
    reducing the number of OSRM calls.
    """
    from logic.gap_fill_log import GapFillLog  # local import to avoid circular dependency

    state = GapFillState()
    csv_files = [f for f in os.listdir(folder) if f.endswith("_output.csv")]

    for filename in csv_files:
        path = os.path.join(folder, filename)

        if not state.needs_processing(path):
            continue

        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        date_str = date_match.group(1) if date_match else filename

        try:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                fieldnames = list(reader.fieldnames or [])

            if not rows:
                continue

            if "synthetic" not in fieldnames:
                fieldnames.append("synthetic")
            for row in rows:
                row.setdefault("synthetic", "False")

            # Group by journey, sort by timestamp
            grouped = {}
            order = []
            for row in rows:
                jid = row.get("journey_id", "0")
                if jid not in grouped:
                    grouped[jid] = []
                    order.append(jid)
                grouped[jid].append(row)

            gap_log = GapFillLog()
            gap_log.clear_date(date_str)

            gap_filled_rows = []
            for jid in order:
                journey_rows = sorted(grouped[jid], key=lambda r: r.get("timestamp", ""))
                filled, gaps, pts = fill_journey_gaps(journey_rows)
                gap_filled_rows.extend(filled)
                if gaps > 0:
                    try:
                        gap_log.record(date_str, int(jid), gaps, pts)
                    except ValueError:
                        pass
                    print(f"  Road gap-fill: journey {jid} on {date_str}: {gaps} gap(s), {pts} point(s) added")

            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(gap_filled_rows)

            state.mark_processed(path)

        except Exception as e:
            print(f"Gap fill error on {filename}: {e}")


def fill_journey_gaps(journey_rows):
    """
    Scan a single journey's rows for consecutive pairs further than
    ROAD_FILL_MIN_KM apart and insert synthetic road-following points.

    Makes ONE OSRM request for the whole journey (or a small number of
    batched requests for very long journeys) rather than one per gap.

    Returns:
        filled_rows  : list of row dicts with synthetic rows inserted
        gaps_filled  : number of gaps that received synthetic points
        points_added : total synthetic points inserted
    """
    if len(journey_rows) < 2:
        return list(journey_rows), 0, 0

    # Find which consecutive pairs need filling — skip pairs involving synthetic points
    # (those are already road-following from auto-merge bridges)
    gap_indices = set()
    for i in range(len(journey_rows) - 1):
        if (journey_rows[i].get("synthetic", "False").strip().lower() == "true" or
                journey_rows[i + 1].get("synthetic", "False").strip().lower() == "true"):
            continue
        try:
            lat1 = float(journey_rows[i]["latitude"])
            lon1 = float(journey_rows[i]["longitude"])
            lat2 = float(journey_rows[i + 1]["latitude"])
            lon2 = float(journey_rows[i + 1]["longitude"])
        except (ValueError, KeyError):
            continue
        if haversine(lat1, lon1, lat2, lon2) > ROAD_FILL_MIN_KM:
            gap_indices.add(i)

    if not gap_indices:
        return list(journey_rows), 0, 0

    # ONE OSRM call for the whole journey
    # Only pass real (non-synthetic) points as waypoints; we must preserve ordering
    # of all rows but only route between real GPS anchors.
    all_coords = []
    for r in journey_rows:
        try:
            all_coords.append((float(r["latitude"]), float(r["longitude"])))
        except (ValueError, KeyError):
            all_coords.append((0.0, 0.0))

    leg_geometries = _get_all_legs(all_coords)
    if leg_geometries is None:
        print("Gap filler: OSRM unavailable, skipping road fill for this journey")
        return list(journey_rows), 0, 0

    # Build output — insert interior road points only for gap legs
    filled_rows = []
    gaps_filled = 0
    points_added = 0

    for i, row in enumerate(journey_rows[:-1]):
        filled_rows.append(row)

        if i not in gap_indices or i >= len(leg_geometries):
            continue

        leg = leg_geometries[i]
        interior = leg[1:-1] if len(leg) > 2 else []
        if not interior:
            continue

        next_row = journey_rows[i + 1]
        try:
            t1 = datetime.fromisoformat(row["timestamp"])
            t2 = datetime.fromisoformat(next_row["timestamp"])
            alt1 = float(row.get("altitude", 0))
            alt2 = float(next_row.get("altitude", 0))
        except (ValueError, KeyError):
            continue

        gap_seconds = (t2 - t1).total_seconds()
        n = len(interior)
        device = row.get("dev_esp32", "esp32_device_001")
        jid = row.get("journey_id", "1")

        for j, (lat, lon) in enumerate(interior):
            frac = (j + 1) / (n + 1)
            ts = t1 + timedelta(seconds=frac * gap_seconds)
            alt = alt1 + frac * (alt2 - alt1)
            filled_rows.append({
                "dev_esp32": device,
                "timestamp": ts.isoformat(),
                "altitude": f"{alt:.1f}",
                "latitude": f"{lat:.6f}",
                "longitude": f"{lon:.6f}",
                "journey_id": jid,
                "synthetic": "True",
            })

        gaps_filled += 1
        points_added += n

    # Append the final real row
    filled_rows.append(journey_rows[-1])

    return filled_rows, gaps_filled, points_added
