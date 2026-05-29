from datetime import datetime
from logic.calculate import haversine

# --- Tunable thresholds ---
# Pass 1 — tight jitter: small clouds of GPS noise while stationary
MIN_CLUSTER_RADIUS_KM = 0.01   # 10 metres
MIN_CLUSTER_SIZE = 3           # min consecutive points to be a cluster

# Pass 2 — large stationary periods: device sitting in a wider area for a long time
MIN_CLUSTER_RADIUS_KM_2 = 0.2  # 200 metres
MIN_CLUSTER_SIZE_2 = 100       # min consecutive points to be a cluster

MIN_JOURNEY_DISTANCE_KM = 0.1  # discard entire journeys under this total distance
MIN_JOURNEY_AVG_SPEED_KMH = 5.0  # discard entire journeys with avg speed below this
MIN_STRAIGHTNESS_RATIO = 0.15   # net displacement / path length; below this = random-walk drift


# ----------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------

def _classify_segments(rows, radius_km, min_size):
    """
    Split rows into (type, [rows]) segments where type is 'cluster' or 'track'.

    Each point is compared to the *first* point of the current buffer.
    If it stays within radius_km it stays in the buffer.
    When a point moves beyond that radius the buffer is committed:
      - min_size+ points → 'cluster' (stationary GPS noise)
      - fewer points     → 'track'   (genuine movement)
    """
    if not rows:
        return []

    segments = []
    buffer = [rows[0]]

    for curr in rows[1:]:
        ref = buffer[0]
        try:
            dist = haversine(
                float(ref["latitude"]), float(ref["longitude"]),
                float(curr["latitude"]), float(curr["longitude"])
            )
        except (ValueError, KeyError):
            dist = 0.0

        if dist < radius_km:
            buffer.append(curr)
        else:
            seg_type = "cluster" if len(buffer) >= min_size else "track"
            segments.append((seg_type, buffer))
            buffer = [curr]

    seg_type = "cluster" if len(buffer) >= min_size else "track"
    segments.append((seg_type, buffer))
    return segments


def _filter_by_journey_distance(kept):
    """
    Drop entire journeys whose surviving points:
      - total distance < MIN_JOURNEY_DISTANCE_KM, OR
      - average speed  < MIN_JOURNEY_AVG_SPEED_KMH

    Returns (filtered_rows, valid_jids, rejection_reason_by_jid).
    """
    grouped = {}
    for row in kept:
        try:
            jid = int(row.get("journey_id", 0))
        except (ValueError, TypeError):
            jid = 0
        grouped.setdefault(jid, [])
        grouped[jid].append(row)

    valid_jids = set()
    rejection_reason = {}
    for jid, pts in grouped.items():
        total = 0.0
        for i in range(1, len(pts)):
            try:
                total += haversine(
                    float(pts[i-1]["latitude"]), float(pts[i-1]["longitude"]),
                    float(pts[i]["latitude"]), float(pts[i]["longitude"])
                )
            except (ValueError, TypeError):
                continue

        if total < MIN_JOURNEY_DISTANCE_KM:
            rejection_reason[jid] = f"Too short (< {MIN_JOURNEY_DISTANCE_KM * 1000:.0f} m total)"
            continue

        # Use moving time (sum of inter-point gaps capped per gap) so that stops
        # within a journey (e.g. parked cluster removed by the cluster filter)
        # do not artificially lower the average speed.
        _MAX_GAP_S = 60.0
        moving_s = 0.0
        for i in range(1, len(pts)):
            try:
                ta = datetime.fromisoformat(pts[i - 1]["timestamp"])
                tb = datetime.fromisoformat(pts[i]["timestamp"])
                moving_s += min((tb - ta).total_seconds(), _MAX_GAP_S)
            except (ValueError, KeyError):
                pass

        avg_speed = (total / (moving_s / 3600.0)) if moving_s > 0 else 0.0

        if avg_speed < MIN_JOURNEY_AVG_SPEED_KMH and avg_speed > 0:
            rejection_reason[jid] = (
                f"Too slow (avg {avg_speed:.1f} km/h < {MIN_JOURNEY_AVG_SPEED_KMH} km/h)"
            )
            continue

        # Straightness: net displacement / path length.
        # Random-walk GPS drift wanders across a wide area but ends near where it
        # started, giving a very low ratio. Genuine travel makes net progress.
        if total > 0:
            try:
                net_disp = haversine(
                    float(pts[0]["latitude"]), float(pts[0]["longitude"]),
                    float(pts[-1]["latitude"]), float(pts[-1]["longitude"])
                )
                straightness = net_disp / total
            except (ValueError, KeyError):
                straightness = 1.0
            if straightness < MIN_STRAIGHTNESS_RATIO:
                rejection_reason[jid] = (
                    f"Random-walk drift (straightness {straightness:.3f} < {MIN_STRAIGHTNESS_RATIO})"
                )
                continue

        valid_jids.add(jid)

    return [row for row in kept if int(row.get("journey_id", 0)) in valid_jids], valid_jids, rejection_reason


def _group_by_journey(rows):
    """Return an ordered list of (jid, [rows]) preserving original journey order."""
    groups = {}
    order = []
    for row in rows:
        try:
            jid = int(row.get("journey_id", 0))
        except (ValueError, TypeError):
            jid = 0
        if jid not in groups:
            groups[jid] = []
            order.append(jid)
        groups[jid].append(row)
    return [(jid, groups[jid]) for jid in order]


def _apply_cluster_passes(journey_rows):
    """
    Run both cluster passes on a single journey's rows.
    Returns (kept_rows, removed_with_reasons).
    Each journey is processed in isolation so that a cluster at the end of one
    journey cannot bleed into the start of the next.
    """
    removed = []

    segs1 = _classify_segments(journey_rows, MIN_CLUSTER_RADIUS_KM, MIN_CLUSTER_SIZE)
    after_pass1 = []
    for seg_type, seg_rows in segs1:
        if seg_type == "track":
            after_pass1.extend(seg_rows)
        else:
            reason = (
                f"Drift cluster ({len(seg_rows)} pts within "
                f"{MIN_CLUSTER_RADIUS_KM * 1000:.0f} m)"
            )
            for row in seg_rows:
                removed.append((row, reason))

    segs2 = _classify_segments(after_pass1, MIN_CLUSTER_RADIUS_KM_2, MIN_CLUSTER_SIZE_2)
    after_pass2 = []
    for seg_type, seg_rows in segs2:
        if seg_type == "track":
            after_pass2.extend(seg_rows)
        else:
            reason = (
                f"Large stationary cluster ({len(seg_rows)} pts within "
                f"{MIN_CLUSTER_RADIUS_KM_2 * 1000:.0f} m)"
            )
            for row in seg_rows:
                removed.append((row, reason))

    return after_pass2, removed


# ----------------------------------------------------------------
# Public API
# ----------------------------------------------------------------

def filter_rows(rows):
    """
    Remove GPS drift noise from a list of CSV row dicts.

    Filters applied (in order):
      1. Per-journey pass 1 — tight cluster (10 m / 3 pts): removes GPS jitter.
      2. Per-journey pass 2 — large cluster (200 m / 100 pts): removes long
         stationary periods. Each journey is filtered independently to prevent
         cross-journey cluster bleeding (e.g. Journey N+1 starting at the same
         location Journey N ended).
      3. Journey filter: entire journeys whose remaining points cover less than
         MIN_JOURNEY_DISTANCE_KM or avg speed < MIN_JOURNEY_AVG_SPEED_KMH are
         discarded.
    """
    if not rows:
        return []

    after_clusters = []
    for _, journey_rows in _group_by_journey(rows):
        kept, _ = _apply_cluster_passes(journey_rows)
        after_clusters.extend(kept)

    result, _, _ = _filter_by_journey_distance(after_clusters)
    return result


def filter_rows_with_reasons(rows):
    """
    Same logic as filter_rows() but also returns removed rows with reasons.

    Returns:
        kept_rows : list of row dicts that passed all filters
        removed   : list of (row, reason_str) tuples
    """
    if not rows:
        return [], []

    removed = []
    after_clusters = []

    for _, journey_rows in _group_by_journey(rows):
        kept, journey_removed = _apply_cluster_passes(journey_rows)
        after_clusters.extend(kept)
        removed.extend(journey_removed)

    kept_rows, valid_jids, rejection_reason = _filter_by_journey_distance(after_clusters)

    for row in after_clusters:
        jid = int(row.get("journey_id", 0))
        if jid not in valid_jids:
            reason = rejection_reason.get(jid, "Journey filtered")
            removed.append((row, reason))

    return kept_rows, removed
