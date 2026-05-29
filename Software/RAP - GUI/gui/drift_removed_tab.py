import csv
import os
from collections import Counter
from datetime import datetime
from tkinter import ttk
import tkinter as tk
from tkintermapview import TkinterMapView

from logic import file_index
from logic.calculate import haversine
from logic.gps_filter import filter_rows_with_reasons
from config import documents_folder, filtered_folder


def _read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _journey_distance(rows):
    total = 0.0
    for i in range(1, len(rows)):
        try:
            total += haversine(
                float(rows[i - 1]["latitude"]), float(rows[i - 1]["longitude"]),
                float(rows[i]["latitude"]), float(rows[i]["longitude"])
            )
        except (ValueError, KeyError):
            continue
    return total


def _primary_reason(reason_list):
    """Return the most common reason string from a list."""
    if not reason_list:
        return ""
    return Counter(reason_list).most_common(1)[0][0]


def _compute_diff(date):
    """
    Run filter_rows_with_reasons on raw data for a date.
    Returns list of per-journey dicts:
      {date, jid, raw_count, kept_count, removed_count, removed_km,
       primary_reason, status, removed_rows, kept_rows}
    """
    filename = f"esp32_device_001_{date}_output.csv"
    raw_rows = _read_csv(os.path.join(documents_folder, filename))
    if not raw_rows:
        return []

    _, removed_with_reasons = filter_rows_with_reasons(raw_rows)

    # Build kept timestamp set from filtered file (ground truth)
    filt_rows = _read_csv(os.path.join(filtered_folder, filename))
    kept_ts = {r["timestamp"] for r in filt_rows}

    # Group raw rows by journey_id
    raw_by_jid = {}
    for r in raw_rows:
        try:
            jid = int(r["journey_id"])
        except (ValueError, KeyError):
            jid = 0
        raw_by_jid.setdefault(jid, [])
        raw_by_jid[jid].append(r)

    # Build per-row reason lookup from filter analysis
    reason_by_ts = {r["timestamp"]: reason for r, reason in removed_with_reasons}

    results = []
    for jid in sorted(raw_by_jid.keys()):
        pts = raw_by_jid[jid]
        removed_rows = [r for r in pts if r["timestamp"] not in kept_ts]
        kept_rows = [r for r in pts if r["timestamp"] in kept_ts]

        reasons = [reason_by_ts.get(r["timestamp"], "Unknown") for r in removed_rows]

        if len(removed_rows) == 0:
            status = "Unaffected"
        elif len(kept_rows) == 0:
            status = "Fully removed"
        else:
            status = "Partially filtered"

        raw_km = _journey_distance(pts)
        kept_km = _journey_distance(kept_rows)
        removed_km = raw_km - kept_km

        results.append({
            "date": date,
            "jid": jid,
            "raw_count": len(pts),
            "kept_count": len(kept_rows),
            "removed_count": len(removed_rows),
            "raw_km": raw_km,
            "kept_km": kept_km,
            "removed_km": removed_km,
            "primary_reason": _primary_reason(reasons) if removed_rows else "",
            "status": status,
            "removed_rows": removed_rows,
            "kept_rows": kept_rows,
        })

    return results


# ----------------------------------------------------------------
# Drift-specific map window
# ----------------------------------------------------------------
class DriftMapWindow:
    """Shows kept (blue) and removed (red) GPS points side-by-side."""

    def __init__(self, parent, journey_data):
        """
        journey_data: list of {date, jid, kept_rows, removed_rows}
        """
        self.window = tk.Toplevel(parent)
        self.window.title("Drift Removed — Map View")
        self.window.geometry("950x680")

        self.map_widget = TkinterMapView(self.window, width=950, height=630, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(-36.8485, 174.7633)
        self.map_widget.set_zoom(10)

        ttk.Label(
            self.window,
            text="Blue = kept points   |   Red = removed (drift) points"
        ).pack(pady=4)

        self._draw(journey_data)

    def _to_latlon(self, rows):
        pts = []
        for r in rows:
            try:
                pts.append((float(r["latitude"]), float(r["longitude"])))
            except (ValueError, KeyError):
                continue
        return pts

    def _draw(self, journey_data):
        all_pts = []
        for jd in journey_data:
            kept = self._to_latlon(jd["kept_rows"])
            removed = self._to_latlon(jd["removed_rows"])
            label = f"J{jd['jid']} ({jd['date']})"

            if len(kept) >= 2:
                self.map_widget.set_path(kept, color="blue", width=3)
            if len(removed) >= 2:
                self.map_widget.set_path(removed, color="red", width=2)
            elif len(removed) == 1:
                self.map_widget.set_marker(
                    removed[0][0], removed[0][1],
                    text=f"{label} removed pt",
                    marker_color_circle="red",
                    marker_color_outside="darkred"
                )

            all_pts.extend(kept + removed)

        if all_pts:
            avg_lat = sum(p[0] for p in all_pts) / len(all_pts)
            avg_lon = sum(p[1] for p in all_pts) / len(all_pts)
            self.map_widget.set_position(avg_lat, avg_lon)
            self.map_widget.set_zoom(13)


# ----------------------------------------------------------------
# Tab
# ----------------------------------------------------------------
class DriftRemovedTab:
    def __init__(self, parent, settings, deleted):
        self.settings = settings
        self.deleted = deleted
        self.frame = ttk.Frame(parent)
        self.file_dates = file_index.scan_available_dates(folder=documents_folder)
        self._row_data = []  # list of result dicts matching table rows
        self.build_ui()

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def build_ui(self):
        ttk.Label(
            self.frame, text="Drift-Removed Data", font=("Arial", 13, "bold")
        ).pack(pady=(12, 2))
        ttk.Label(
            self.frame,
            text="Points removed by the GPS drift filter. Select year, and optionally month and day to narrow the data.",
            foreground="gray"
        ).pack(pady=(0, 8))

        # --- Date selection ---
        date_frame = ttk.Frame(self.frame)
        date_frame.pack(pady=6)

        ttk.Label(date_frame, text="Year:").grid(row=0, column=0, padx=4)
        years = sorted(self.file_dates.keys())
        self.year_combo = ttk.Combobox(date_frame, values=years, state="readonly", width=8)
        self.year_combo.grid(row=0, column=1, padx=4)
        self.year_combo.bind("<<ComboboxSelected>>", self._on_year)

        ttk.Label(date_frame, text="Month (optional):").grid(row=0, column=2, padx=4)
        self.month_combo = ttk.Combobox(date_frame, values=[], state="readonly", width=10)
        self.month_combo.grid(row=0, column=3, padx=4)
        self.month_combo.bind("<<ComboboxSelected>>", self._on_month)

        ttk.Label(date_frame, text="Day (optional):").grid(row=0, column=4, padx=4)
        self.day_combo = ttk.Combobox(date_frame, values=[], state="readonly", width=6)
        self.day_combo.grid(row=0, column=5, padx=4)

        ttk.Button(date_frame, text="Load", command=self.load_diff).grid(row=0, column=6, padx=10)

        # --- Table + scrollbar ---
        table_frame = ttk.Frame(self.frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=4)

        self._sort_col = None
        self._sort_reverse = False

        cols = ("date", "journey", "raw_pts", "kept_pts", "removed_pts",
                "removed_km", "primary_reason", "status")
        self.table = ttk.Treeview(
            table_frame, columns=cols, show="headings", height=13,
            selectmode="extended"
        )
        self._col_labels = {
            "date": "Date",
            "journey": "Journey",
            "raw_pts": "Raw Pts",
            "kept_pts": "Kept Pts",
            "removed_pts": "Removed Pts",
            "removed_km": "Removed (km)",
            "primary_reason": "Primary Reason",
            "status": "Status",
        }
        for col, text in self._col_labels.items():
            self.table.heading(col, text=text,
                               command=lambda c=col: self._sort_by_col(c))

        self.table.column("date",           width=100, anchor="center")
        self.table.column("journey",        width=70,  anchor="center")
        self.table.column("raw_pts",        width=75,  anchor="center")
        self.table.column("kept_pts",       width=75,  anchor="center")
        self.table.column("removed_pts",    width=90,  anchor="center")
        self.table.column("removed_km",     width=100, anchor="center")
        self.table.column("primary_reason", width=230, anchor="w")
        self.table.column("status",         width=145, anchor="center")

        self.table.tag_configure("removed",    foreground="red")
        self.table.tag_configure("partial",    foreground="darkorange")
        self.table.tag_configure("unaffected", foreground="green")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")

        # --- Bottom buttons ---
        bottom = ttk.Frame(self.frame)
        bottom.pack(pady=6)
        ttk.Button(bottom, text="Show on Map", command=self.show_on_map).pack(side="left", padx=10)

        self.status_lbl = ttk.Label(self.frame, text="", foreground="gray")
        self.status_lbl.pack(pady=4)

    # ------------------------------------------------------------
    # SORTING
    # ------------------------------------------------------------
    _SORT_KEYS = {
        "date":           lambda r: r["date"],
        "journey":        lambda r: r["jid"],
        "raw_pts":        lambda r: r["raw_count"],
        "kept_pts":       lambda r: r["kept_count"],
        "removed_pts":    lambda r: r["removed_count"],
        "removed_km":     lambda r: r["removed_km"],
        "primary_reason": lambda r: r["primary_reason"],
        "status":         lambda r: r["status"],
    }

    def _sort_by_col(self, col):
        if not self._row_data:
            return
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col = col
            self._sort_reverse = False

        key_fn = self._SORT_KEYS.get(col, lambda r: "")
        self._row_data.sort(key=key_fn, reverse=self._sort_reverse)

        for c, label in self._col_labels.items():
            arrow = (" ▲" if not self._sort_reverse else " ▼") if c == col else ""
            self.table.heading(c, text=label + arrow)

        self._repopulate_table()

    def _repopulate_table(self):
        self.table.delete(*self.table.get_children())
        for r in self._row_data:
            tag = "unaffected"
            if r["status"] == "Fully removed":
                tag = "removed"
            elif r["status"] == "Partially filtered":
                tag = "partial"
            self.table.insert("", "end", tags=(tag,), values=(
                r["date"],
                r["jid"],
                r["raw_count"],
                r["kept_count"],
                r["removed_count"],
                f"{r['removed_km']:.3f}",
                r["primary_reason"],
                r["status"],
            ))

    # ------------------------------------------------------------
    # DROPDOWN LOGIC
    # ------------------------------------------------------------
    def _on_year(self, event=None):
        try:
            year = int(self.year_combo.get())
        except ValueError:
            return
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]
        self.month_combo["values"] = month_names
        self.month_combo.set("")
        self.day_combo["values"] = []
        self.day_combo.set("")

    def _on_month(self, event=None):
        try:
            year = int(self.year_combo.get())
            month_num = datetime.strptime(self.month_combo.get(), "%B").month
        except ValueError:
            return
        days = sorted(self.file_dates.get(year, {}).get(month_num, []))
        self.day_combo["values"] = days
        self.day_combo.set("")

    # ------------------------------------------------------------
    # LOAD DIFF
    # ------------------------------------------------------------
    def load_diff(self):
        try:
            year = int(self.year_combo.get())
        except ValueError:
            self.status_lbl.config(text="Select at least a year", foreground="red")
            return

        month_str = self.month_combo.get().strip()
        day_str = self.day_combo.get().strip()

        if month_str:
            try:
                month_num = datetime.strptime(month_str, "%B").month
            except ValueError:
                self.status_lbl.config(text="Invalid month selection", foreground="red")
                return
            if day_str:
                dates = [f"{year}-{month_num:02d}-{int(day_str):02d}"]
            else:
                days = sorted(self.file_dates.get(year, {}).get(month_num, []))
                dates = [f"{year}-{month_num:02d}-{d:02d}" for d in days]
        else:
            # No month selected — load all months for the year
            dates = []
            for month_num in sorted(self.file_dates.get(year, {}).keys()):
                days = sorted(self.file_dates.get(year, {}).get(month_num, []))
                dates.extend(f"{year}-{month_num:02d}-{d:02d}" for d in days)

        self.status_lbl.config(text=f"Loading {len(dates)} day(s)...", foreground="blue")
        self.frame.update_idletasks()

        all_results = []
        for date in dates:
            all_results.extend(_compute_diff(date))

        self.table.delete(*self.table.get_children())
        self._row_data = []

        if not all_results:
            self.status_lbl.config(text="No raw data found for selection", foreground="red")
            return

        total_removed = sum(r["removed_count"] for r in all_results)
        total_km = sum(r["removed_km"] for r in all_results)

        self._row_data = all_results
        self._sort_col = None
        self._sort_reverse = False
        for c, label in self._col_labels.items():
            self.table.heading(c, text=label)
        self._repopulate_table()

        label = dates[0] if len(dates) == 1 else f"{dates[0]} → {dates[-1]}"
        self.status_lbl.config(
            text=f"{label}: {total_removed} pts removed ({total_km:.3f} km) across {len(all_results)} journeys",
            foreground="gray"
        )

    # ------------------------------------------------------------
    # MAP
    # ------------------------------------------------------------
    def show_on_map(self):
        selected = self.table.selection()
        if not selected:
            self.status_lbl.config(text="Select one or more rows to map", foreground="red")
            return

        indices = [self.table.index(iid) for iid in selected]
        journey_data = [self._row_data[i] for i in indices if i < len(self._row_data)]

        if not journey_data:
            return

        DriftMapWindow(self.frame, journey_data)
