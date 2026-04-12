import tkinter as tk
from tkinter import Label, ttk
from datetime import datetime
from tkinter.ttk import Combobox
from tkintermapview import TkinterMapView
import os
import csv

from updater import auto_update
import db_pull
import calculate
from config import documents_folder, APP_VERSION


class MileageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Access Program")
        self.root.geometry("750x700")

        self.selected_journeys = {}

        self.setup()
        self.build_ui()

    # ---------------- SETUP ----------------
    def setup(self):
        db_pull.get_all_items()
        self.file_dates = self.scan_available_dates()

    # ---------------- SCAN FILES ----------------
    def scan_available_dates(self):
        """Scan documents_folder for esp32_device_001_YYYY-MM-DD_output.csv files."""
        dates = {}

        for filename in os.listdir(documents_folder):
            if not filename.endswith("_output.csv"):
                continue

            parts = filename.split("_")
            if len(parts) < 4:
                continue

            date_str = parts[3]  # correct position for YYYY-MM-DD

            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            year = dt.year
            month = dt.month
            day = dt.day

            dates.setdefault(year, {})
            dates[year].setdefault(month, [])
            dates[year][month].append(day)

        return dates

    # ---------------- UI BUILD ----------------
    def build_ui(self):
        # Banner
        banner = tk.Frame(self.root, bg="blue", height=40)
        banner.pack(fill="x")

        tk.Label(
            banner,
            text="Mileage Logger",
            bg="blue",
            fg="white",
            font=("Arial", 16, "bold")
        ).pack(pady=5)

        # -------- DAY SELECT --------
        Label(self.root, text="Select a Day:", font=("Arial", 12)).pack(pady=10)

        dropdown_frame = tk.Frame(self.root)
        dropdown_frame.pack(pady=5)

        # Year dropdown
        years = sorted(self.file_dates.keys())
        self.year_combo = Combobox(dropdown_frame, values=years, state="readonly", width=8)
        self.year_combo.pack(side="left", padx=5)

        # Month dropdown
        self.month_combo = Combobox(dropdown_frame, values=[], state="readonly", width=12)
        self.month_combo.pack(side="left", padx=5)

        # Day dropdown
        self.day_combo = Combobox(dropdown_frame, values=[], state="readonly", width=5)
        self.day_combo.pack(side="left", padx=5)

        # Bind updates
        self.year_combo.bind("<<ComboboxSelected>>", self.update_month_dropdown)
        self.month_combo.bind("<<ComboboxSelected>>", self.update_day_dropdown)

        # -------- BUTTON ROW (ONE LINE) --------
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Show Journeys",
                  command=self.show_journeys).pack(side="left", padx=5)

        tk.Button(button_frame, text="Show This Month's Mileage",
                  command=self.show_mileage_month).pack(side="left", padx=5)

        tk.Button(button_frame, text="Show This Year's Mileage",
                  command=self.show_mileage_year).pack(side="left", padx=5)

        # Status label
        self.status_label = tk.Label(self.root, text="", font=("Arial", 10), fg="red")
        self.status_label.pack(pady=5)

        # -------- JOURNEY TABLE --------
        Label(self.root, text="Journeys for Selected Day:", font=("Arial", 12)).pack(pady=10)

        self.table = ttk.Treeview(
            self.root,
            columns=("check", "journey", "start", "end", "duration", "distance"),
            show="headings",
            height=12
        )

        self.table.heading("check", text="✓")
        self.table.heading("journey", text="Journey")
        self.table.heading("start", text="Start Time")
        self.table.heading("end", text="End Time")
        self.table.heading("duration", text="Duration")
        self.table.heading("distance", text="Distance (km)")

        self.table.column("check", width=40, anchor="center")
        self.table.column("journey", width=80, anchor="center")
        self.table.column("start", width=140)
        self.table.column("end", width=140)
        self.table.column("duration", width=120, anchor="center")
        self.table.column("distance", width=120, anchor="center")

        self.table.bind("<Button-1>", self.toggle_checkbox)
        self.table.pack(pady=10)

        # -------- SHOW SELECTED JOURNEYS BUTTON (UNDER TABLE) --------
        self.map_selected_btn = tk.Button(
            self.root,
            text="Show Selected Journeys on Map",
            command=self.show_selected_journeys_on_map
        )
        self.map_selected_btn.pack(pady=10)

        # Current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        tk.Label(self.root, text=f"Current Date: {current_date}",
                 font=("Arial", 10), fg="gray").pack(side="bottom", pady=5)

    # ---------------- DROPDOWN UPDATES ----------------
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

    # ---------------- CHECKBOX HANDLER ----------------
    def toggle_checkbox(self, event):
        region = self.table.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.table.identify_row(event.y)
        col = self.table.identify_column(event.x)

        if col != "#1":  # checkbox column
            return

        jid = self.table.set(row_id, "journey")

        self.selected_journeys[jid] = not self.selected_journeys.get(jid, False)
        self.table.set(row_id, "check", "✓" if self.selected_journeys[jid] else "")

    # ---------------- JOURNEY TABLE ----------------
    def load_journey_table(self, selected_date):
        for row in self.table.get_children():
            self.table.delete(row)

        filename = f"esp32_device_001_{selected_date}_output.csv"
        path = os.path.join(documents_folder, filename)

        if not os.path.exists(path):
            self.status_label.config(text="No data file for this date.", fg="red")
            return

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        journeys = {}

        for row in rows:
            jid = int(row["journey_id"])
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

            self.selected_journeys[str(jid)] = False

            self.table.insert(
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

    # ---------------- CALLBACKS ----------------
    def get_selected_date(self):
        year = self.year_combo.get()
        month_name = self.month_combo.get()
        day = self.day_combo.get()

        if not (year and month_name and day):
            self.status_label.config(text="Please select year, month, and day.", fg="red")
            return None

        month_num = datetime.strptime(month_name, "%B").month
        return f"{year}-{month_num:02d}-{int(day):02d}"

    def show_journeys(self):
        selected_date = self.get_selected_date()
        if not selected_date:
            return

        self.load_journey_table(selected_date)
        self.status_label.config(text=f"Journeys loaded for {selected_date}", fg="green")

    def show_selected_journeys_on_map(self):
        selected_date = self.get_selected_date()
        if not selected_date:
            return

        selected_ids = [int(j) for j, checked in self.selected_journeys.items() if checked]

        if not selected_ids:
            self.status_label.config(text="No journeys selected.", fg="red")
            return

        coords_by_journey = calculate.getCoords(selected_date, "esp32_device_001", journey_id=selected_ids)
        print("Selected:", self.selected_journeys)

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

            colors = self.get_color_gradient(len(coords) - 1)

            for i in range(len(coords) - 1):
                map_widget.set_path([coords[i], coords[i+1]], color=colors[i], width=4)

            map_widget.set_marker(coords[0][0], coords[0][1], text=f"Start J{jid}")
            map_widget.set_marker(coords[-1][0], coords[-1][1], text=f"End J{jid}")

    def show_mileage_month(self):
        month_name = self.month_combo.get()
        year_str = self.year_combo.get()
        total_km, message = calculate.mileageMonth(month_name, year_str)

        self.status_label.config(
            text=f"{message}\nTotal: {total_km:.2f} km",
            fg="green" if total_km > 0 else "red"
        )

    def show_mileage_year(self):
        year_str = self.year_combo.get()
        total_km, message = calculate.mileageYear(year_str)

        self.status_label.config(
            text=f"{message}\nTotal: {total_km:.2f} km",
            fg="green" if total_km > 0 else "red"
        )

    # ---------------- UTIL ----------------
    def get_color_gradient(self, n):
        colors = []
        for i in range(n):
            r = int(255 * (i / (n - 1)))
            g = 0
            b = int(255 * (1 - i / (n - 1)))
            colors.append(f"#{r:02x}{g:02x}{b:02x}")
        return colors


# ---------------- ENTRY POINT ----------------
def main():
    auto_update()
    root = tk.Tk()
    app = MileageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()