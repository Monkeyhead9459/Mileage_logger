import tkinter as tk
from tkinter import ttk
from tkinter.ttk import Combobox
from datetime import datetime

import os
from logic import file_index
from logic import journey_loader
from logic import journey_merge
from config import documents_folder, filtered_folder
from logic.csv_export import export_single_day
from logic.mileage import mileage_month, mileage_year
from gui.map_window import MapWindow


class SingleDayTab:
    def __init__(self, parent, settings, deleted, folder=None):
        self.settings = settings
        self.deleted = deleted
        self.folder = folder if folder is not None else filtered_folder
        self.frame = ttk.Frame(parent)

        # Load available dates from logic layer
        self.file_dates = file_index.scan_available_dates(folder=self.folder)

        # Track selected journeys
        self.selected_journeys = {}

        self.build_ui()

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def build_ui(self):
        # --- Date selection ---
        date_frame = ttk.Frame(self.frame)
        date_frame.pack(pady=10)

        ttk.Label(date_frame, text="Select a Day:", font=("Arial", 12)).pack()

        dropdowns = ttk.Frame(date_frame)
        dropdowns.pack(pady=5)

        years = sorted(self.file_dates.keys())
        self.year_combo = Combobox(dropdowns, values=years, state="readonly", width=8)
        self.year_combo.pack(side="left", padx=5)

        self.month_combo = Combobox(dropdowns, values=[], state="readonly", width=12)
        self.month_combo.pack(side="left", padx=5)

        self.day_combo = Combobox(dropdowns, values=[], state="readonly", width=5)
        self.day_combo.pack(side="left", padx=5)

        self.year_combo.bind("<<ComboboxSelected>>", self.update_month_dropdown)
        self.month_combo.bind("<<ComboboxSelected>>", self.update_day_dropdown)

        # --- Buttons ---
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Show Journeys", command=self.show_journeys).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="This Month's Mileage", command=self.show_month_mileage).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="This Year's Mileage", command=self.show_year_mileage).pack(side="left", padx=5)

        # --- Table ---
        ttk.Label(self.frame, text="Journeys for Selected Day:", font=("Arial", 12)).pack(pady=10)

        self.table = ttk.Treeview(
            self.frame,
            columns=("check", "journey", "start", "end", "duration", "distance", "avg_speed", "max_speed"),
            show="headings",
            height=12
        )

        for col, text, width in [
            ("check", "✓", 40),
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

        self.table["displaycolumns"] = ("check", "journey", "start", "end", "duration", "distance")
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

        # --- Bottom buttons ---
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
    def update_month_dropdown(self, event=None):
        year = self.year_combo.get()
        if not year:
            return

        year = int(year)
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]

        self.month_combo["values"] = month_names
        if month_names:
            self.month_combo.current(0)
            self.update_day_dropdown()

    def update_day_dropdown(self, event=None):
        year = self.year_combo.get()
        month_name = self.month_combo.get()
        if not (year and month_name):
            return

        year = int(year)
        month_num = datetime.strptime(month_name, "%B").month
        days = sorted(self.file_dates.get(year, {}).get(month_num, []))

        self.day_combo["values"] = days
        if days:
            self.day_combo.current(0)

    # ------------------------------------------------------------
    # LOAD JOURNEYS
    # ------------------------------------------------------------
    def get_selected_date(self):
        year = self.year_combo.get()
        month_name = self.month_combo.get()
        day = self.day_combo.get()

        if not (year and month_name and day):
            self.status.config(text="Select year, month, and day")
            return None

        month_num = datetime.strptime(month_name, "%B").month
        return f"{year}-{month_num:02d}-{int(day):02d}"

    def set_debug_columns(self, debug):
        if debug:
            self.table["displaycolumns"] = ("check", "journey", "start", "end", "duration", "distance", "avg_speed", "max_speed")
            self.merge_btn.pack(side="left", padx=10)
            self.archive_btn.pack(side="left", padx=10)
        else:
            self.table["displaycolumns"] = ("check", "journey", "start", "end", "duration", "distance")
            self.merge_btn.pack_forget()
            self.archive_btn.pack_forget()

    def get_active_folder(self):
        return self.folder

    def refresh_dates(self):
        self.file_dates = file_index.scan_available_dates(folder=self.folder)
        years = sorted(self.file_dates.keys())
        self.year_combo["values"] = years
        self.month_combo["values"] = []
        self.day_combo["values"] = []
        self.year_combo.set("")
        self.month_combo.set("")
        self.day_combo.set("")

    def show_journeys(self):
        date = self.get_selected_date()
        if not date:
            return

        journeys = journey_loader.load_single_day(date, self.deleted, folder=self.get_active_folder())
        self.populate_table(journeys)
        self.status.config(text=f"Journeys loaded for {date}", foreground="green")

    def populate_table(self, journeys):
        # Clear table
        for row in self.table.get_children():
            self.table.delete(row)

        self.selected_journeys.clear()
        self.select_all_var.set(False)

        for j in journeys:
            jid = j["journey_id"]
            self.selected_journeys[str(jid)] = False

            start_time = j["start_time"].split("T")[1].split("+")[0]
            end_time = j["end_time"].split("T")[1].split("+")[0]
            display_jid = j.get("merged_from") or str(jid)

            self.table.insert(
                "",
                "end",
                iid=str(jid),
                values=(
                    "",
                    display_jid,
                    start_time,
                    end_time,
                    j["duration"],
                    f"{j['distance']:.2f}",
                    f"{j.get('avg_speed', 0):.1f}",
                    f"{j.get('max_speed', 0):.1f}",
                )
            )

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

        self.selected_journeys[row_id] = not self.selected_journeys.get(row_id, False)
        self.table.set(row_id, "check", "✓" if self.selected_journeys[row_id] else "")

    def toggle_select_all(self):
        select_all = self.select_all_var.get()
        for row_id in self.table.get_children():
            self.selected_journeys[row_id] = select_all
            self.table.set(row_id, "check", "✓" if select_all else "")

    # ------------------------------------------------------------
    # MAP DISPLAY
    # ------------------------------------------------------------
    def show_on_map(self):
        date = self.get_selected_date()
        if not date:
            return

        selected_ids = [int(j) for j, v in self.selected_journeys.items() if v]
        if not selected_ids:
            self.status.config(text="No journeys selected")
            return

        coords = journey_loader.get_coords(date, selected_ids, folder=self.get_active_folder())
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

    def show_month_mileage(self):
        month = self.month_combo.get()
        year = self.year_combo.get()
        if not (month and year):
            self.status.config(text="Select year and month")
            return

        km, msg = mileage_month(month, year, self.deleted, folder=self.get_active_folder())
        self.status.config(text=f"{msg}  Total: {km:.2f} km", foreground="green")

    def show_year_mileage(self):
        year = self.year_combo.get()
        if not year:
            self.status.config(text="Select year")
            return

        km, msg = mileage_year(year, self.deleted, folder=self.get_active_folder())
        self.status.config(text=f"{msg}  Total: {km:.2f} km", foreground="green")

    # ------------------------------------------------------------
    # MERGE
    # ------------------------------------------------------------
    def merge_journeys(self):
        date = self.get_selected_date()
        if not date:
            return

        selected_ids = [int(j) for j, v in self.selected_journeys.items() if v]
        if len(selected_ids) < 2:
            self.status.config(text="Select at least 2 journeys to merge", foreground="red")
            return

        self.status.config(text="Merging via OSRM road routing...", foreground="blue")
        self.frame.update_idletasks()

        ok, msg = journey_merge.merge_journeys(date, selected_ids, self.get_active_folder())
        if ok:
            self.show_journeys()
            self.status.config(text=msg, foreground="green")
        else:
            self.status.config(text=f"Merge failed: {msg}", foreground="red")

    # ------------------------------------------------------------
    # ARCHIVE
    # ------------------------------------------------------------
    def archive_selected(self):
        date = self.get_selected_date()
        if not date:
            return

        selected_ids = [int(j) for j, v in self.selected_journeys.items() if v]
        if not selected_ids:
            self.status.config(text="No journeys selected", foreground="red")
            return

        self.deleted.archive(date, selected_ids)
        self.show_journeys()
        self.status.config(text=f"Archived journey(s): {selected_ids}", foreground="green")

    # ------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------
    def export_selected(self):
        date = self.get_selected_date()
        if not date:
            return

        selected_ids = [int(j) for j, v in self.selected_journeys.items() if v]
        if not selected_ids:
            self.status.config(text="No journeys selected")
            return

        # Load journeys again (logic layer handles everything)
        journeys = journey_loader.load_single_day(date, self.deleted, folder=self.get_active_folder())

        # Filter selected
        export_rows = []
        for j in journeys:
            if j["journey_id"] in selected_ids:
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