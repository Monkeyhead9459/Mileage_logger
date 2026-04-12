import tkinter as tk
from tkinter import Label
from datetime import datetime
from tkcalendar import DateEntry
from tkinter.ttk import Combobox
from tkinter import ttk
from tkintermapview import TkinterMapView
import os

from updater import auto_update
import db_pull
import calculate
from config import documents_folder, APP_VERSION

print(documents_folder) 

class MileageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote Access Program")
        self.root.geometry("500x500")

        self.setup()
        self.build_ui()

    # ---------------- SETUP ----------------
    def setup(self):
        db_pull.get_all_items()

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
            font=("Arial", 14, "bold")
        ).pack(pady=5)

        # -------- DAY SELECT --------
        day_frame = tk.Frame(self.root)
        day_frame.pack(pady=10)

        Label(day_frame, text="Select a Day:").pack(pady=10)

        # Store calendar widget as a class attribute
        self.cal = DateEntry(day_frame, width=12, background='blue',
                             foreground='white', borderwidth=2)
        self.cal.pack(pady=5)

        tk.Button(day_frame, text="Show This Day's Mileage",
                  command=self.show_mileage_day).pack(side="left", padx=10)

        tk.Button(day_frame, text="Show Map",
                  command=self.show_map).pack(side="left", padx=10)

        tk.Label(self.root, text="").pack(pady=20)

        # -------- MONTH SELECT --------
        month_frame = tk.Frame(self.root)
        month_frame.pack(pady=10)

        Label(month_frame, text="Select Month & Year:").pack(pady=10)

        monthbtn_frame = tk.Frame(month_frame)
        monthbtn_frame.pack(pady=10)

        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        self.month_combo = Combobox(monthbtn_frame, values=months, state="readonly")
        self.month_combo.pack(side="left", padx=10)

        current_year = datetime.now().year
        years = [str(current_year - i) for i in range(5)]

        self.year_combo = Combobox(monthbtn_frame, values=years, state="readonly")
        self.year_combo.current(0)
        self.year_combo.pack(side="left", padx=10)

        tk.Button(month_frame, text="Show This Month's Mileage",
                  command=self.show_mileage_month).pack(side="left", padx=10)

        tk.Button(month_frame, text="Show This Year's Mileage",
                  command=self.show_mileage_year).pack(side="left", padx=10)

        # Status label
        self.status_label = tk.Label(self.root, text="", font=("Arial", 10), fg="red")
        self.status_label.pack(pady=5)

        # Current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        tk.Label(self.root, text=f"Current Date: {current_date}",
                 font=("Arial", 10), fg="gray").pack(side="bottom", pady=5)

    # ---------------- CALLBACKS ----------------
    def show_map(self):
        selected_date = self.cal.get_date().strftime("%Y-%m-%d")
        coords = calculate.getCoords(selected_date, device="esp32_device_001")

        map_window = tk.Toplevel(self.root)
        map_window.title(f"GPS Path on {selected_date}")
        map_window.geometry("800x600")

        map_widget = TkinterMapView(map_window, width=800, height=600, corner_radius=0)
        map_widget.pack(fill="both", expand=True)

        map_widget.set_position(coords[0][0], coords[0][1])
        map_widget.set_zoom(14)

        colors = self.get_color_gradient(len(coords) - 1)

        for i in range(len(coords) - 1):
            map_widget.set_path([coords[i], coords[i+1]], color=colors[i], width=4)

        map_widget.set_marker(coords[0][0], coords[0][1], text="Start")
        map_widget.set_marker(coords[-1][0], coords[-1][1], text="End")

    def show_mileage_day(self):
        selected_date = self.cal.get_date().strftime("%Y-%m-%d")
        total_km, message = calculate.mileageDay(selected_date)

        if total_km == 0:
            self.status_label.config(text=message, fg="red")
        else:
            self.status_label.config(
                text=f"Distance on {selected_date}: {total_km:.2f} km\n{message}",
                fg="green"
            )

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
    auto_update()  # updater stays outside the class
    root = tk.Tk()
    app = MileageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()