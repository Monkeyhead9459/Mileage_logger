import tkinter as tk
from tkinter import ttk
from tkinter.ttk import Combobox
from datetime import datetime, timedelta

import os
from logic import file_index
from logic import journey_loader
from logic import journey_merge
from config import documents_folder, filtered_folder
from logic.csv_export import export_single_day
from logic.mileage import mileage_month, mileage_year
from gui.map_window import MapWindow


class RangeTab:
    def __init__(self, parent, settings, deleted, folder=None):
        self.settings = settings
        self.deleted = deleted
        self.folder = folder if folder is not None else filtered_folder
        self.frame = ttk.Frame(parent)

        # Load available dates
        self.file_dates = file_index.scan_available_dates(folder=self.folder)

        # Track selected journeys
        self.selected_journeys = {}

        self.build_ui()

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def set_debug_columns(self, debug):
        if debug:
            self.table["displaycolumns"] = ("check", "date", "journey", "start", "end", "duration", "distance", "avg_speed", "max_speed")
            self.merge_btn.pack(side="left", padx=10)
            self.archive_btn.pack(side="left", padx=10)
        else:
            self.table["displaycolumns"] = ("check", "date", "journey", "start", "end", "duration", "distance")
            self.merge_btn.pack_forget()
            self.archive_btn.pack_forget()

    def get_active_folder(self):
        return self.folder

    def refresh_dates(self):
        self.file_dates = file_index.scan_available_dates(folder=self.folder)
        years = sorted(self.file_dates.keys())
        self.start_year["values"] = years
        self.end_year["values"] = years
        for combo in [self.start_year, self.start_month, self.start_day,
                      self.end_year, self.end_month, self.end_day]:
            combo.set("")

    def build_ui(self):
        # --- Date Range Selection ---
        date_frame = ttk.Frame(self.frame)
        date_frame.pack(pady=10)

        ttk.Label(date_frame, text="Select Date Range:", font=("Arial", 12)).pack()

        dropdowns = ttk.Frame(date_frame)
        dropdowns.pack(pady=5)

        # Start date
        self.start_year = Combobox(dropdowns, width=6, state="readonly")
        self.start_month = Combobox(dropdowns, width=10, state="readonly")
        self.start_day = Combobox(dropdowns, width=5, state="readonly")

        # End date
        self.end_year = Combobox(dropdowns, width=6, state="readonly")
        self.end_month = Combobox(dropdowns, width=10, state="readonly")
        self.end_day = Combobox(dropdowns, width=5, state="readonly")

        for widget in [
            self.start_year, self.start_month, self.start_day,
            self.end_year, self.end_month, self.end_day
        ]:
            widget.pack(side="left", padx=4)

        # Populate year dropdowns
        years = sorted(self.file_dates.keys())
        self.start_year["values"] = years
        self.end_year["values"] = years

        self.start_year.bind("<<ComboboxSelected>>", self.update_start_month)
        self.start_month.bind("<<ComboboxSelected>>", self.update_start_day)

        self.end_year.bind("<<ComboboxSelected>>", self.update_end_month)
        self.end_month.bind("<<ComboboxSelected>>", self.update_end_day)

        # --- Buttons ---
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Show Journeys", command=self.show_journeys).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Mileage (Range)", command=self.show_range_mileage).pack(side="left", padx=5)

        # --- Table ---
        ttk.Label(self.frame, text="Journeys in Range:", font=("Arial", 12)).pack(pady=10)

        self.table = ttk.Treeview(
            self.frame,
            columns=("check", "date", "journey", "start", "end", "duration", "distance", "avg_speed", "max_speed"),
            show="headings",
            height=14
        )

        for col, text, width in [
            ("check", "✓", 40),
            ("date", "Date", 100),
            ("journey", "Journey", 70),
            ("start", "Start Time", 120),
            ("end", "End Time", 120),
            ("duration", "Duration", 120),
            ("distance", "Distance (km)", 110),
            ("avg_speed", "Avg Speed (km/h)", 120),
            ("max_speed", "Max Speed (km/h)", 120),
        ]:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center")

        self.table["displaycolumns"] = ("check", "date", "journey", "start", "end", "duration", "distance")
        self.table.bind("<Button-1>", self.toggle_checkbox)
        self.table.pack(pady=10, fill="x")

        # --- Select All ---
        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(
            self.frame,
            text="Select All Journeys",
            variable=self.select_all_var,
            command=self.toggle_select_all
        ).pack(pady=(0, 10))

        # --- Bottom Buttons ---
        bottom = ttk.Frame(self.frame)
        bottom.pack(pady=10)

        is_raw = os.path.normpath(self.folder) == os.path.normpath(documents_folder)
        ttk.Button(bottom, text="Show on Map", command=self.show_on_map).pack(side="left", padx=10)
        ttk.Button(bottom, text="Mileage (Selected)", command=self.mileage_selected).pack(side="left", padx=10)
        ttk.Button(bottom, text="Export CSV", command=self.export_selected).pack(side="left", padx=10)
        self.merge_btn = ttk.Button(bottom, text="Merge Journeys", command=self.merge_journeys)
        self.archive_btn = ttk.Button(bottom, text="Archive Selected", command=self.archive_selected)
        if is_raw:
            self.merge_btn.config(state="disabled")
            self.archive_btn.config(state="disabled")
        # Hidden by default — shown only in debug mode

        # Status label
        self.status = ttk.Label(self.frame, text="", foreground="red")
        self.status.pack(pady=5)

    # ------------------------------------------------------------
    # DROPDOWN LOGIC
    # ------------------------------------------------------------
    def update_start_month(self, event=None):
        year = int(self.start_year.get())
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]
        self.start_month["values"] = month_names
        if month_names:
            self.start_month.current(0)
            self.update_start_day()

    def update_start_day(self, event=None):
        year = int(self.start_year.get())
        month_num = datetime.strptime(self.start_month.get(), "%B").month
        days = sorted(self.file_dates.get(year, {}).get(month_num, []))
        self.start_day["values"] = days
        if days:
            self.start_day.current(0)

    def update_end_month(self, event=None):
        year = int(self.end_year.get())
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]
        self.end_month["values"] = month_names
        if month_names:
            self.end_month.current(0)
            self.update_end_day()

    def update_end_day(self, event=None):
        year = int(self.end_year.get())
        month_num = datetime.strptime(self.end_month.get(), "%B").month
        days = sorted(self.file_dates.get(year, {}).get(month_num, []))
        self.end_day["values"] = days
        if days:
            self.end_day.current(0)

    # ------------------------------------------------------------
    # RANGE LOADING
    # ------------------------------------------------------------
    def get_range(self):
        try:
            start = datetime(
                int(self.start_year.get()),
                datetime.strptime(self.start_month.get(), "%B").month,
                int(self.start_day.get())
            )
            end = datetime(
                int(self.end_year.get()),
                datetime.strptime(self.end_month.get(), "%B").month,
                int(self.end_day.get())
            )
        except Exception:
            self.status.config(text="Select valid start and end dates")
            return None, None

        if end < start:
            self.status.config(text="End date must be after start date")
            return None, None

        return start, end

    def show_journeys(self):
        start, end = self.get_range()
        if not start:
            return

        # Clear table
        for row in self.table.get_children():
            self.table.delete(row)

        self.selected_journeys.clear()
        self.select_all_var.set(False)

        # Iterate through date range
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            journeys = journey_loader.load_single_day(date_str, self.deleted, folder=self.get_active_folder())

            for j in journeys:
                jid = j["journey_id"]
                key = f"{date_str}:{jid}"
                self.selected_journeys[key] = False

                start_time = j["start_time"].split("T")[1].split("+")[0]
                end_time = j["end_time"].split("T")[1].split("+")[0]
                display_jid = j.get("merged_from") or str(jid)

                self.table.insert(
                    "",
                    "end",
                    iid=key,
                    values=(
                        "",
                        date_str,
                        display_jid,
                        start_time,
                        end_time,
                        j["duration"],
                        f"{j['distance']:.2f}",
                        f"{j.get('avg_speed', 0):.1f}",
                        f"{j.get('max_speed', 0):.1f}",
                    )
                )

            current += timedelta(days=1)

        self.status.config(text="Journeys loaded", foreground="green")

    # ------------------------------------------------------------
    # CHECKBOX LOGIC
    # ------------------------------------------------------------
    def toggle_checkbox(self, event):
        region = self.table.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.table.identify_row(event.y)
        col = self.table.identify_column(event.x)
        if col != "#1":
            return

        key = row_id
        self.selected_journeys[key] = not self.selected_journeys.get(key, False)
        self.table.set(row_id, "check", "✓" if self.selected_journeys[key] else "")

    def toggle_select_all(self):
        select_all = self.select_all_var.get()
        for row_id in self.table.get_children():
            self.selected_journeys[row_id] = select_all
            self.table.set(row_id, "check", "✓" if select_all else "")

    # ------------------------------------------------------------
    # MAP DISPLAY
    # ------------------------------------------------------------
    def show_on_map(self):
        selected = {}

        for row_id in self.table.get_children():
            if self.selected_journeys.get(row_id, False):
                date, jid_str = row_id.split(":", 1)
                selected.setdefault(date, [])
                selected[date].append(int(jid_str))

        if not selected:
            self.status.config(text="No journeys selected")
            return

        # Load coords for all selected journeys
        coords = {}
        for date, ids in selected.items():
            coords.update(journey_loader.get_coords(date, ids, folder=self.get_active_folder()))

        MapWindow(self.frame, coords)

    # ------------------------------------------------------------
    # MILEAGE
    # ------------------------------------------------------------
    def mileage_selected(self):
        total = 0.0
        for row_id in self.table.get_children():
            if self.selected_journeys.get(row_id, False):
                total += float(self.table.set(row_id, "distance"))

        if total == 0:
            self.status.config(text="No journeys selected")
        else:
            self.status.config(text=f"Selected mileage: {total:.2f} km", foreground="green")

    def show_range_mileage(self):
        start, end = self.get_range()
        if not start:
            return

        total = 0.0
        current = start

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            journeys = journey_loader.load_single_day(date_str, self.deleted, folder=self.get_active_folder())
            for j in journeys:
                total += j["distance"]
            current += timedelta(days=1)

        self.status.config(text=f"Range mileage: {total:.2f} km", foreground="green")

    # ------------------------------------------------------------
    # MERGE
    # ------------------------------------------------------------
    def merge_journeys(self):
        # Collect selected journeys grouped by date
        selected = {}
        for row_id in self.table.get_children():
            if self.selected_journeys.get(row_id, False):
                date, jid_str = row_id.split(":", 1)
                selected.setdefault(date, [])
                selected[date].append(int(jid_str))

        if not selected:
            self.status.config(text="No journeys selected", foreground="red")
            return

        if len(selected) > 1:
            self.status.config(text="Merge requires journeys from the same date", foreground="red")
            return

        date = list(selected.keys())[0]
        journey_ids = selected[date]

        if len(journey_ids) < 2:
            self.status.config(text="Select at least 2 journeys to merge", foreground="red")
            return

        self.status.config(text="Merging via OSRM road routing...", foreground="blue")
        self.frame.update_idletasks()

        ok, msg = journey_merge.merge_journeys(date, journey_ids, self.get_active_folder())
        if ok:
            self.show_journeys()
            self.status.config(text=msg, foreground="green")
        else:
            self.status.config(text=f"Merge failed: {msg}", foreground="red")

    # ------------------------------------------------------------
    # ARCHIVE
    # ------------------------------------------------------------
    def archive_selected(self):
        selected = {}
        for row_id in self.table.get_children():
            if self.selected_journeys.get(row_id, False):
                date, jid_str = row_id.split(":", 1)
                selected.setdefault(date, [])
                selected[date].append(int(jid_str))

        if not selected:
            self.status.config(text="No journeys selected", foreground="red")
            return

        for date, ids in selected.items():
            self.deleted.archive(date, ids)

        total = sum(len(v) for v in selected.values())
        self.show_journeys()
        self.status.config(text=f"Archived {total} journey(s)", foreground="green")

    # ------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------
    def export_selected(self):
        selected = {}

        for row_id in self.table.get_children():
            if self.selected_journeys.get(row_id, False):
                date, jid_str = row_id.split(":", 1)
                selected.setdefault(date, [])
                selected[date].append(int(jid_str))

        if not selected:
            self.status.config(text="No journeys selected")
            return

        # Build export rows
        export_rows = []
        for date, ids in selected.items():
            journeys = journey_loader.load_single_day(date, self.deleted, folder=self.get_active_folder())
            for j in journeys:
                if j["journey_id"] in ids:
                    export_rows.append({
                        "_date": date,
                        "_jid": j["journey_id"],
                        "_start": j["start_time"],
                        "_end": j["end_time"],
                        "_duration": j["duration"],
                        "_distance": j["distance"],
                        "_start_lat": j["start_lat"],
                        "_start_lon": j["start_lon"],
                        "_end_lat": j["end_lat"],
                        "_end_lon": j["end_lon"],
                    })

        export_single_day(export_rows, self.settings)
        self.status.config(text="CSV exported", foreground="green")