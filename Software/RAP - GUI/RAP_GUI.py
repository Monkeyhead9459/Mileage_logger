import tkinter as tk
from tkinter import ttk, Label
from datetime import datetime, timedelta
from tkinter.ttk import Combobox
from tkintermapview import TkinterMapView
import os
import csv
import json
import journey  # reverse geocoder used only for CSV export

from updater import auto_update
import db_pull
import calculate
from config import documents_folder, APP_VERSION


DELETED_FILE = os.path.join(documents_folder, "deleted_journeys.json")


class MileageApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Remote Access Program - v{APP_VERSION}")
        self.root.geometry("1100x850")

        self.file_dates = {}
        self.selected_single_journeys = {}
        self.selected_range_journeys = {}
        self.range_internal_map = {}  # (date_str, numeric_id) -> composite_id

        self.deleted_journeys = self.load_deleted_journeys()

        self.setup()
        self.build_ui()

    # ---------------- SETUP ----------------
    def setup(self):
        db_pull.get_all_items()
        self.file_dates = self.scan_available_dates()

    def load_deleted_journeys(self):
        if not os.path.exists(DELETED_FILE):
            return {}
        try:
            with open(DELETED_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_deleted_journeys(self):
        with open(DELETED_FILE, "w") as f:
            json.dump(self.deleted_journeys, f, indent=4)

    def scan_available_dates(self):
        dates = {}
        for filename in os.listdir(documents_folder):
            if not filename.endswith("_output.csv"):
                continue

            parts = filename.split("_")
            if len(parts) < 4:
                continue

            date_str = parts[3]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            year, month, day = dt.year, dt.month, dt.day
            dates.setdefault(year, {})
            dates[year].setdefault(month, [])
            if day not in dates[year][month]:
                dates[year][month].append(day)

        return dates

    # ---------------- UI BUILD ----------------
    def build_ui(self):
        banner = tk.Frame(self.root, bg="blue", height=40)
        banner.pack(fill="x")

        tk.Label(
            banner,
            text="Mileage Logger",
            bg="blue",
            fg="white",
            font=("Arial", 16, "bold")
        ).pack(pady=5)

        self.status_label = tk.Label(self.root, text="", font=("Arial", 10), fg="red")
        self.status_label.pack(pady=5)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.single_tab = tk.Frame(notebook)
        self.range_tab = tk.Frame(notebook)

        notebook.add(self.single_tab, text="Single Day")
        notebook.add(self.range_tab, text="Date Range")

        self.build_single_day_tab()
        self.build_range_tab()

        current_date = datetime.now().strftime("%Y-%m-%d")
        tk.Label(self.root, text=f"Current Date: {current_date}",
                 font=("Arial", 10), fg="gray").pack(side="bottom", pady=5)

    # ---------------- SINGLE DAY TAB ----------------
    def build_single_day_tab(self):
        Label(self.single_tab, text="Select a Day:", font=("Arial", 12)).pack(pady=10)

        dropdown_frame = tk.Frame(self.single_tab)
        dropdown_frame.pack(pady=5)

        years = sorted(self.file_dates.keys())
        self.year_combo = Combobox(dropdown_frame, values=years, state="readonly", width=8)
        self.year_combo.pack(side="left", padx=5)

        self.month_combo = Combobox(dropdown_frame, values=[], state="readonly", width=12)
        self.month_combo.pack(side="left", padx=5)

        self.day_combo = Combobox(dropdown_frame, values=[], state="readonly", width=5)
        self.day_combo.pack(side="left", padx=5)

        self.year_combo.bind("<<ComboboxSelected>>", self.update_month_dropdown_single)
        self.month_combo.bind("<<ComboboxSelected>>", self.update_day_dropdown_single)

        button_frame = tk.Frame(self.single_tab)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Show Journeys",
                  command=self.show_journeys_single).pack(side="left", padx=5)

        tk.Button(button_frame, text="Show This Month's Mileage",
                  command=self.show_mileage_month).pack(side="left", padx=5)

        tk.Button(button_frame, text="Show This Year's Mileage",
                  command=self.show_mileage_year).pack(side="left", padx=5)

        Label(self.single_tab, text="Journeys for Selected Day:", font=("Arial", 12)).pack(pady=10)

        self.single_table = ttk.Treeview(
            self.single_tab,
            columns=("check", "journey", "start", "end", "duration", "distance"),
            show="headings",
            height=12
        )

        for col, text, width in [
            ("check", "✓", 40),
            ("journey", "Journey", 70),
            ("start", "Start Time", 120),
            ("end", "End Time", 120),
            ("duration", "Duration", 120),
            ("distance", "Distance (km)", 120),
        ]:
            self.single_table.heading(col, text=text)
            self.single_table.column(col, width=width, anchor="center")

        self.single_table.bind("<Button-1>", self.toggle_checkbox_single)
        self.single_table.pack(pady=10, fill="x")

        self.select_all_single_var = tk.BooleanVar()
        tk.Checkbutton(
            self.single_tab,
            text="Select All Journeys",
            variable=self.select_all_single_var,
            command=self.toggle_select_all_single
        ).pack(pady=(0, 10))

        bottom_buttons = tk.Frame(self.single_tab)
        bottom_buttons.pack(pady=10)

        tk.Button(
            bottom_buttons,
            text="Show Selected Journeys on Map",
            command=self.show_selected_journeys_on_map
        ).pack(side="left", padx=10)

        tk.Button(
            bottom_buttons,
            text="Mileage for Selected",
            command=self.show_mileage_selected_single
        ).pack(side="left", padx=10)

        tk.Button(
            bottom_buttons,
            text="Create CSV of Selected Journeys",
            command=self.export_selected_single
        ).pack(side="left", padx=10)

        tk.Button(
            bottom_buttons,
            text="Archive Selected Journeys",
            command=self.archive_selected_single
        ).pack(side="left", padx=10)

    # ---------------- RANGE TAB ----------------
    def build_range_tab(self):
        Label(self.range_tab, text="Select Date Range:", font=("Arial", 12)).pack(pady=10)

        years = sorted(self.file_dates.keys())

        range_frame = tk.Frame(self.range_tab)
        range_frame.pack(pady=5)

        # Start date
        tk.Label(range_frame, text="Start:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.start_year = Combobox(range_frame, values=years, state="readonly", width=8)
        self.start_year.grid(row=0, column=1, padx=5, pady=2)

        self.start_month = Combobox(range_frame, values=[], state="readonly", width=12)
        self.start_month.grid(row=0, column=2, padx=5, pady=2)

        self.start_day = Combobox(range_frame, values=[], state="readonly", width=5)
        self.start_day.grid(row=0, column=3, padx=5, pady=2)

        # End date
        tk.Label(range_frame, text="End:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        self.end_year = Combobox(range_frame, values=years, state="readonly", width=8)
        self.end_year.grid(row=1, column=1, padx=5, pady=2)

        self.end_month = Combobox(range_frame, values=[], state="readonly", width=12)
        self.end_month.grid(row=1, column=2, padx=5, pady=2)

        self.end_day = Combobox(range_frame, values=[], state="readonly", width=5)
        self.end_day.grid(row=1, column=3, padx=5, pady=2)

        # Bind dropdowns
        self.start_year.bind("<<ComboboxSelected>>", self.update_start_month)
        self.start_month.bind("<<ComboboxSelected>>", self.update_start_day)
        self.end_year.bind("<<ComboboxSelected>>", self.update_end_month)
        self.end_month.bind("<<ComboboxSelected>>", self.update_end_day)

        tk.Button(
            self.range_tab,
            text="Show Range Journeys",
            command=self.load_range_journeys
        ).pack(pady=10)

        Label(self.range_tab, text="Journeys for Date Range:", font=("Arial", 12)).pack(pady=10)

        self.range_table = ttk.Treeview(
            self.range_tab,
            columns=("check", "date", "journey", "start", "end", "duration", "distance"),
            show="headings",
            height=12
        )

        for col, text, width in [
            ("check", "✓", 40),
            ("date", "Date", 100),
            ("journey", "Journey", 70),
            ("start", "Start Time", 120),
            ("end", "End Time", 120),
            ("duration", "Duration", 120),
            ("distance", "Distance (km)", 120),
        ]:
            self.range_table.heading(col, text=text)
            self.range_table.column(col, width=width, anchor="center")

        self.range_table.bind("<Button-1>", self.toggle_checkbox_range)
        self.range_table.pack(pady=10, fill="x")

        self.select_all_range_var = tk.BooleanVar()
        tk.Checkbutton(
            self.range_tab,
            text="Select All Journeys",
            variable=self.select_all_range_var,
            command=self.toggle_select_all_range
        ).pack(pady=(0, 10))

        bottom_buttons = tk.Frame(self.range_tab)
        bottom_buttons.pack(pady=10)

        tk.Button(
            bottom_buttons,
            text="Mileage for Selected",
            command=self.show_mileage_selected_range
        ).pack(side="left", padx=10)

        tk.Button(
            bottom_buttons,
            text="Create CSV of Selected Journeys",
            command=self.export_selected_range
        ).pack(side="left", padx=10)

        tk.Button(
            bottom_buttons,
            text="Archive Selected Journeys",
            command=self.archive_selected_range
        ).pack(side="left", padx=10)


            # ---------------- DROPDOWNS: SINGLE DAY ----------------
    def update_month_dropdown_single(self, event=None):
        year = self.year_combo.get()
        if not year:
            return
        year = int(year)
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]
        self.month_combo["values"] = month_names
        if month_names:
            self.month_combo.current(0)
            self.update_day_dropdown_single()

    def update_day_dropdown_single(self, event=None):
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

    # ---------------- DROPDOWNS: RANGE ----------------
    def update_start_month(self, event=None):
        year = self.start_year.get()
        if not year:
            return
        year = int(year)
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]
        self.start_month["values"] = month_names
        if month_names:
            self.start_month.current(0)
            self.update_start_day()

    def update_start_day(self, event=None):
        year = self.start_year.get()
        month_name = self.start_month.get()
        if not (year and month_name):
            return
        year = int(year)
        month_num = datetime.strptime(month_name, "%B").month
        days = sorted(self.file_dates.get(year, {}).get(month_num, []))
        self.start_day["values"] = days
        if days:
            self.start_day.current(0)

    def update_end_month(self, event=None):
        year = self.end_year.get()
        if not year:
            return
        year = int(year)
        months = sorted(self.file_dates.get(year, {}).keys())
        month_names = [datetime(2000, m, 1).strftime("%B") for m in months]
        self.end_month["values"] = month_names
        if month_names:
            self.end_month.current(0)
            self.update_end_day()

    def update_end_day(self, event=None):
        year = self.end_year.get()
        month_name = self.end_month.get()
        if not (year and month_name):
            return
        year = int(year)
        month_num = datetime.strptime(month_name, "%B").month
        days = sorted(self.file_dates.get(year, {}).get(month_num, []))
        self.end_day["values"] = days
        if days:
            self.end_day.current(0)

    # ---------------- SINGLE DAY: TABLE + SELECTION ----------------
    def toggle_checkbox_single(self, event):
        region = self.single_table.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.single_table.identify_row(event.y)
        col = self.single_table.identify_column(event.x)
        if col != "#1":
            return

        jid = self.single_table.set(row_id, "journey")
        self.selected_single_journeys[jid] = not self.selected_single_journeys.get(jid, False)
        self.single_table.set(row_id, "check", "✓" if self.selected_single_journeys[jid] else "")

    def toggle_select_all_single(self):
        select_all = self.select_all_single_var.get()
        for row_id in self.single_table.get_children():
            jid = self.single_table.set(row_id, "journey")
            self.selected_single_journeys[jid] = select_all
            self.single_table.set(row_id, "check", "✓" if select_all else "")

    def get_selected_date_single(self):
        year = self.year_combo.get()
        month_name = self.month_combo.get()
        day = self.day_combo.get()

        if not (year and month_name and day):
            self.status_label.config(text="Please select year, month, and day.", fg="red")
            return None

        month_num = datetime.strptime(month_name, "%B").month
        return f"{year}-{month_num:02d}-{int(day):02d}"

    def show_journeys_single(self):
        selected_date = self.get_selected_date_single()
        if not selected_date:
            return
        self.load_journey_table_single(selected_date)
        self.status_label.config(text=f"Journeys loaded for {selected_date}", fg="green")

    def load_journey_table_single(self, selected_date):
        for row in self.single_table.get_children():
            self.single_table.delete(row)
        self.selected_single_journeys.clear()
        self.select_all_single_var.set(False)

        filename = f"esp32_device_001_{selected_date}_output.csv"
        path = os.path.join(documents_folder, filename)

        if not os.path.exists(path):
            self.status_label.config(text="No data file for this date.", fg="red")
            return

        # Load deleted list for this date
        deleted_for_date = self.deleted_journeys.get(selected_date, [])

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        journeys = {}
        for row in rows:
            jid = int(row["journey_id"])
            if jid in deleted_for_date:
                continue  # skip archived journeys
            journeys.setdefault(jid, [])
            journeys[jid].append(row)

        for jid, points in journeys.items():
            points.sort(key=lambda r: r["timestamp"])
            start_time = points[0]["timestamp"]
            end_time = points[-1]["timestamp"]

            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            duration = t2 - t1

            total_dist = 0
            for i in range(len(points) - 1):
                lat1 = float(points[i]["latitude"])
                lon1 = float(points[i]["longitude"])
                lat2 = float(points[i+1]["latitude"])
                lon2 = float(points[i+1]["longitude"])
                total_dist += calculate.haversine(lat1, lon1, lat2, lon2)

            self.selected_single_journeys[str(jid)] = False

            self.single_table.insert(
                "",
                "end",
                values=(
                    "",
                    jid,
                    start_time.split("T")[1].split("+")[0],
                    end_time.split("T")[1].split("+")[0],
                    str(duration),
                    f"{total_dist:.2f}"
                )
            )

    # ---------------- RANGE: TABLE + SELECTION ----------------
    def toggle_checkbox_range(self, event):
        region = self.range_table.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.range_table.identify_row(event.y)
        col = self.range_table.identify_column(event.x)
        if col != "#1":
            return

        display_id = self.range_table.set(row_id, "journey")
        date_str = self.range_table.set(row_id, "date")
        key = (date_str, int(display_id))
        comp_id = self.range_internal_map.get(key)
        if not comp_id:
            return

        self.selected_range_journeys[comp_id] = not self.selected_range_journeys.get(comp_id, False)
        self.range_table.set(row_id, "check", "✓" if self.selected_range_journeys[comp_id] else "")

    def toggle_select_all_range(self):
        select_all = self.select_all_range_var.get()
        for row_id in self.range_table.get_children():
            display_id = self.range_table.set(row_id, "journey")
            date_str = self.range_table.set(row_id, "date")
            key = (date_str, int(display_id))
            comp_id = self.range_internal_map.get(key)
            if not comp_id:
                continue
            self.selected_range_journeys[comp_id] = select_all
            self.range_table.set(row_id, "check", "✓" if select_all else "")


                # ---------------- RANGE DATE HANDLING ----------------
    def get_range_dates(self):
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
            self.status_label.config(text="Invalid date range.", fg="red")
            return None, None

        if end < start:
            self.status_label.config(text="End date must be after start date.", fg="red")
            return None, None

        return start, end

    def load_range_journeys(self):
        start, end = self.get_range_dates()
        if not start:
            return

        for row in self.range_table.get_children():
            self.range_table.delete(row)
        self.selected_range_journeys.clear()
        self.select_all_range_var.set(False)
        self.range_internal_map.clear()

        current = start
        all_rows = []

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            filename = f"esp32_device_001_{date_str}_output.csv"
            path = os.path.join(documents_folder, filename)

            if os.path.exists(path):
                with open(path, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["_date"] = date_str
                        all_rows.append(row)

            current += timedelta(days=1)

        if not all_rows:
            self.status_label.config(text="No data in this range.", fg="red")
            return

        # Build deleted lookup
        deleted_lookup = self.deleted_journeys

        journeys = {}
        for row in all_rows:
            date_str = row["_date"]
            jid = int(row["journey_id"])

            # Skip archived
            if jid in deleted_lookup.get(date_str, []):
                continue

            comp_id = f"{date_str}_J{jid}"
            journeys.setdefault(comp_id, [])
            journeys[comp_id].append(row)

        for comp_id, points in journeys.items():
            points.sort(key=lambda r: r["timestamp"])
            date_str = points[0]["_date"]
            start_time = points[0]["timestamp"]
            end_time = points[-1]["timestamp"]

            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            duration = t2 - t1

            total_dist = 0
            for i in range(len(points) - 1):
                lat1 = float(points[i]["latitude"])
                lon1 = float(points[i]["longitude"])
                lat2 = float(points[i+1]["latitude"])
                lon2 = float(points[i+1]["longitude"])
                total_dist += calculate.haversine(lat1, lon1, lat2, lon2)

            numeric_id = int(points[0]["journey_id"])
            self.selected_range_journeys[comp_id] = False
            self.range_internal_map[(date_str, numeric_id)] = comp_id

            self.range_table.insert(
                "",
                "end",
                values=(
                    "",
                    date_str,
                    numeric_id,
                    start_time.split("T")[1].split("+")[0],
                    end_time.split("T")[1].split("+")[0],
                    str(duration),
                    f"{total_dist:.2f}"
                )
            )

        self.status_label.config(text="Range journeys loaded.", fg="green")

    # ---------------- MAP DISPLAY (SINGLE DAY ONLY) ----------------
    def show_selected_journeys_on_map(self):
        selected_date = self.get_selected_date_single()
        if not selected_date:
            return

        selected_ids = [int(j) for j, checked in self.selected_single_journeys.items() if checked]
        if not selected_ids:
            self.status_label.config(text="No journeys selected.", fg="red")
            return

        coords_by_journey = calculate.getCoords(selected_date, "esp32_device_001", journey_id=selected_ids)

        map_window = tk.Toplevel(self.root)
        map_window.title(f"Selected Journeys on {selected_date}")
        map_window.geometry("800x600")

        map_widget = TkinterMapView(map_window, width=800, height=600, corner_radius=0)
        map_widget.pack(fill="both", expand=True)

        first = True
        for jid in selected_ids:
            coords = coords_by_journey.get(jid, [])
            if not coords:
                continue

            if first:
                map_widget.set_position(coords[0][0], coords[0][1])
                map_widget.set_zoom(14)
                first = False

            if len(coords) > 1:
                colors = self.get_color_gradient(len(coords) - 1)
                for i in range(len(coords) - 1):
                    map_widget.set_path([coords[i], coords[i+1]], color=colors[i], width=4)

            map_widget.set_marker(coords[0][0], coords[0][1], text=f"Start J{jid}")
            map_widget.set_marker(coords[-1][0], coords[-1][1], text=f"End J{jid}")

    # ---------------- MILEAGE CALCULATIONS ----------------
    def show_mileage_selected_single(self):
        total = 0.0
        for row_id in self.single_table.get_children():
            jid = self.single_table.set(row_id, "journey")
            if self.selected_single_journeys.get(jid, False):
                dist = float(self.single_table.set(row_id, "distance"))
                total += dist

        if total == 0:
            self.status_label.config(text="No journeys selected.", fg="red")
        else:
            self.status_label.config(
                text=f"Total distance for selected journeys (single day): {total:.2f} km",
                fg="green"
            )

    def show_mileage_selected_range(self):
        total = 0.0
        for row_id in self.range_table.get_children():
            display_id = self.range_table.set(row_id, "journey")
            date_str = self.range_table.set(row_id, "date")
            key = (date_str, int(display_id))
            comp_id = self.range_internal_map.get(key)
            if comp_id and self.selected_range_journeys.get(comp_id, False):
                dist = float(self.range_table.set(row_id, "distance"))
                total += dist

        if total == 0:
            self.status_label.config(text="No journeys selected in range.", fg="red")
        else:
            self.status_label.config(
                text=f"Total distance for selected journeys (range): {total:.2f} km",
                fg="green"
            )

    # ---------------- ARCHIVE (SOFT DELETE) ----------------
    def archive_selected_single(self):
        selected_date = self.get_selected_date_single()
        if not selected_date:
            return

        archived = self.deleted_journeys.setdefault(selected_date, [])

        for row_id in self.single_table.get_children():
            jid = int(self.single_table.set(row_id, "journey"))
            if self.selected_single_journeys.get(str(jid), False):
                if jid not in archived:
                    archived.append(jid)

        self.save_deleted_journeys()
        self.load_journey_table_single(selected_date)
        self.status_label.config(text="Selected journeys archived.", fg="green")

    def archive_selected_range(self):
        start, end = self.get_range_dates()
        if not start:
            return

        for row_id in self.range_table.get_children():
            date_str = self.range_table.set(row_id, "date")
            jid = int(self.range_table.set(row_id, "journey"))
            key = (date_str, jid)
            comp_id = self.range_internal_map.get(key)

            if comp_id and self.selected_range_journeys.get(comp_id, False):
                archived = self.deleted_journeys.setdefault(date_str, [])
                if jid not in archived:
                    archived.append(jid)

        self.save_deleted_journeys()
        self.load_range_journeys()
        self.status_label.config(text="Selected journeys archived.", fg="green")

    # ---------------- COLOR GRADIENT ----------------
    def get_color_gradient(self, n):
        if n <= 0:
            return ["#ff0000"]
        if n == 1:
            return ["#ff0000"]
        colors = []
        for i in range(n):
            r = int(255 * (i / (n - 1)))
            g = 0
            b = int(255 * (1 - i / (n - 1)))
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
        return colors
    
    def show_mileage_month(self):
        month_name = self.month_combo.get()
        year_str = self.year_combo.get()
        if not (month_name and year_str):
            self.status_label.config(text="Select year and month first.", fg="red")
            return

        total_km, message = calculate.mileageMonth(month_name, year_str)
        self.status_label.config(
            text=f"{message}\nTotal: {total_km:.2f} km",
            fg="green" if total_km > 0 else "red"
        )

    def show_mileage_year(self):
        year_str = self.year_combo.get()
        if not year_str:
            self.status_label.config(text="Select year first.", fg="red")
            return

        total_km, message = calculate.mileageYear(year_str)
        self.status_label.config(
            text=f"{message}\nTotal: {total_km:.2f} km",
            fg="green" if total_km > 0 else "red"
        )

       # ---------------- CSV EXPORT HELPERS ----------------
    def reverse_geocode_short(self, lat, lon, cache):
        """Reverse geocode with caching, return 'street, suburb'."""
        key = (round(lat, 6), round(lon, 6))
        if key in cache:
            return cache[key]

        try:
            full_addr = journey.reverse_geocode(lat, lon)
        except Exception:
            full_addr = "Unknown"

        parts = full_addr.split(",")
        if len(parts) >= 2:
            short_addr = f"{parts[0].strip()}, {parts[1].strip()}"
        else:
            short_addr = full_addr

        cache[key] = short_addr
        return short_addr

    def export_summary_csv(self, rows, filename):
        """Write summary CSV with reverse-geocoded start/end zones."""
        cache = {}
        out_path = os.path.join(documents_folder, filename)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "date", "journey", "start_time", "end_time",
                "start_zone", "end_zone", "duration", "distance_km"
            ])

            for row in rows:
                date_str = row["_date"]
                jid = row["_jid"]
                start_time = row["_start"]
                end_time = row["_end"]
                duration = row["_duration"]
                distance = row["_distance"]

                # Reverse geocode start/end
                start_zone = self.reverse_geocode_short(
                    row["_start_lat"], row["_start_lon"], cache
                )
                end_zone = self.reverse_geocode_short(
                    row["_end_lat"], row["_end_lon"], cache
                )

                writer.writerow([
                    date_str,
                    jid,
                    start_time,
                    end_time,
                    start_zone,
                    end_zone,
                    duration,
                    f"{distance:.2f}"
                ])

        self.status_label.config(text=f"CSV created: {filename}", fg="green")

    # ---------------- EXPORT: SINGLE DAY ----------------
    def export_selected_single(self):
        selected_date = self.get_selected_date_single()
        if not selected_date:
            return

        selected_ids = [
            int(j) for j, checked in self.selected_single_journeys.items() if checked
        ]
        if not selected_ids:
            self.status_label.config(text="No journeys selected.", fg="red")
            return

        filename = f"selected_journeys_{selected_date}.csv"

        # Load raw data
        path = os.path.join(
            documents_folder,
            f"esp32_device_001_{selected_date}_output.csv"
        )
        if not os.path.exists(path):
            self.status_label.config(text="Data file missing.", fg="red")
            return

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Group by journey
        grouped = {}
        for r in rows:
            jid = int(r["journey_id"])
            if jid in selected_ids:
                grouped.setdefault(jid, [])
                grouped[jid].append(r)

        export_rows = []
        for jid, pts in grouped.items():
            pts.sort(key=lambda r: r["timestamp"])
            start = pts[0]
            end = pts[-1]

            start_time = start["timestamp"]
            end_time = end["timestamp"]

            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            duration = str(t2 - t1)

            # Distance
            total_dist = 0
            for i in range(len(pts) - 1):
                lat1 = float(pts[i]["latitude"])
                lon1 = float(pts[i]["longitude"])
                lat2 = float(pts[i+1]["latitude"])
                lon2 = float(pts[i+1]["longitude"])
                total_dist += calculate.haversine(lat1, lon1, lat2, lon2)

            export_rows.append({
                "_date": selected_date,
                "_jid": jid,
                "_start": start_time,
                "_end": end_time,
                "_duration": duration,
                "_distance": total_dist,
                "_start_lat": float(start["latitude"]),
                "_start_lon": float(start["longitude"]),
                "_end_lat": float(end["latitude"]),
                "_end_lon": float(end["longitude"]),
            })

        self.export_summary_csv(export_rows, filename)

    # ---------------- EXPORT: RANGE ----------------
    def export_selected_range(self):
        start, end = self.get_range_dates()
        if not start:
            return

        selected = [
            comp_id for comp_id, checked in self.selected_range_journeys.items()
            if checked
        ]
        if not selected:
            self.status_label.config(text="No journeys selected.", fg="red")
            return

        filename = (
            f"selected_journeys_{start.strftime('%Y-%m-%d')}"
            f"_to_{end.strftime('%Y-%m-%d')}.csv"
        )

        # Load all rows in range
        all_rows = []
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            path = os.path.join(
                documents_folder,
                f"esp32_device_001_{date_str}_output.csv"
            )
            if os.path.exists(path):
                with open(path, newline="") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        r["_date"] = date_str
                        all_rows.append(r)
            current += timedelta(days=1)

        # Group by composite ID
        grouped = {}
        for r in all_rows:
            date_str = r["_date"]
            jid = int(r["journey_id"])
            comp_id = f"{date_str}_J{jid}"
            if comp_id in selected:
                grouped.setdefault(comp_id, [])
                grouped[comp_id].append(r)

        export_rows = []
        for comp_id, pts in grouped.items():
            pts.sort(key=lambda r: r["timestamp"])
            start = pts[0]
            endp = pts[-1]

            start_time = start["timestamp"]
            end_time = endp["timestamp"]

            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            duration = str(t2 - t1)

            total_dist = 0
            for i in range(len(pts) - 1):
                lat1 = float(pts[i]["latitude"])
                lon1 = float(pts[i]["longitude"])
                lat2 = float(pts[i+1]["latitude"])
                lon2 = float(pts[i+1]["longitude"])
                total_dist += calculate.haversine(lat1, lon1, lat2, lon2)

            date_str = start["_date"]
            jid = int(start["journey_id"])

            export_rows.append({
                "_date": date_str,
                "_jid": jid,
                "_start": start_time,
                "_end": end_time,
                "_duration": duration,
                "_distance": total_dist,
                "_start_lat": float(start["latitude"]),
                "_start_lon": float(start["longitude"]),
                "_end_lat": float(endp["latitude"]),
                "_end_lon": float(endp["longitude"]),
            })

        self.export_summary_csv(export_rows, filename)

    # ---------------- MAIN ----------------
def main():
    auto_update()
    root = tk.Tk()
    app = MileageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main() 