import tkinter as tk
from tkinter import Label
from datetime import datetime
import webbrowser
from tkcalendar import DateEntry
from tkinter.ttk import Combobox
from tkinter import ttk
from tkintermapview import TkinterMapView
import csv
import os
import math
import db_pull
import calculate
import importlib
importlib.reload(calculate)

documents_folder = os.path.expanduser("~/Documents/ESP32/Mileage Logger GIT/Mileage_logger/RAP - GUI/Outputs")

def setup():
    db_pull.get_all_items()

def get_color_gradient(n):
    """Generate n colors from blue → red."""
    colors = []
    for i in range(n):
        r = int(255 * (i / (n - 1)))       # Red increases
        g = 0
        b = int(255 * (1 - i / (n - 1)))   # Blue decreases
        colors.append(f"#{r:02x}{g:02x}{b:02x}")
    return colors

def show_map():
    selected_date = cal.get_date().strftime("%Y-%m-%d")
    coords = calculate.getCoords(selected_date, device="esp32_device_001")

    # Create a new top-level window for the map
    map_window = tk.Toplevel(root)
    map_window.title(f"GPS Path on {selected_date}")
    map_window.geometry("800x600")

    map_widget = TkinterMapView(map_window, width=800, height=600, corner_radius=0)
    map_widget.pack(fill="both", expand=True)

    # Center map
    map_widget.set_position(coords[0][0], coords[0][1])
    map_widget.set_zoom(14)

    # Create gradient colors for each segment
    colors = get_color_gradient(len(coords)-1)

    # Draw each segment separately with its own color
    for i in range(len(coords)-1):
        map_widget.set_path([coords[i], coords[i+1]], color=colors[i], width=4)

    # Mark start/end
    map_widget.set_marker(coords[0][0], coords[0][1], text="Start")
    map_widget.set_marker(coords[-1][0], coords[-1][1], text="End")

def show_mileage_day():
    selected_date = cal.get_date().strftime("%Y-%m-%d")
    print("Using mileageDay from:", calculate.mileageDay)
    print("MileageDay signature:", calculate.mileageDay.__code__.co_varnames, calculate.mileageDay.__code__.co_argcount)

    total_km, message = calculate.mileageDay(selected_date)
    if total_km == 0:
        status_label.config(text=message, fg="red")
    else:
        status_label.config(
            text=f"Distance on {selected_date}: {total_km:.2f} km\n{message}",
            fg="green"
        )

def show_mileage_month():
    month_name = month_combo.get()
    year_str = year_combo.get()
    total_km, message = calculate.mileageMonth(month_name, year_str)
    status_label.config(
        text=f"{message}\nTotal: {total_km:.2f} km",
        fg="green" if total_km > 0 else "red"
    )

def show_mileage_year():
    year_str = year_combo.get()
    total_km, message = calculate.mileageYear(year_str)
    status_label.config(
        text=f"{message}\nTotal: {total_km:.2f} km",
        fg="green" if total_km > 0 else "red"
    )

setup()
root = tk.Tk()
root.title("Remote Access Program")
root.geometry("500x500")

# Simulated title banner
banner = tk.Frame(root, bg="blue", height=40)
banner.pack(fill="x")

banner_label = tk.Label(banner, text="Mileage Logger", bg="blue", fg="white", font=("Arial", 14, "bold"))
banner_label.pack(pady=5)


# --------DAY SELECT --------
day_frame = tk.Frame(root)
day_frame.pack(pady=10)

Label(day_frame, text="Select a Day:").pack(pady=10)

# DateEntry widget (calendar dropdown)
cal = DateEntry(day_frame, width=12, background='blue', foreground='white', borderwidth=2)
cal.pack(pady=5)

print("CALCULATE MODULE LOCATION:", calculate)
daybtn = tk.Button(day_frame, text="Show This Days Mileage", command=show_mileage_day)
daybtn.pack(side="left", padx=10)

mapbtn = tk.Button(day_frame, text="Show Map", command=show_map)
mapbtn.pack(side="left", padx=10)

tk.Label(root, text="").pack(pady=20)  # empty line for vertical gap

#-------Month Select--------

month_frame = tk.Frame(root)
month_frame.pack(pady=10)

Label(month_frame, text="Select Month & Year:").pack(pady=10)

monthbtn_frame = tk.Frame(month_frame)
monthbtn_frame.pack(pady=10)

months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

month_combo = Combobox(monthbtn_frame, values=months, state="readonly")
month_combo.pack(side="left", padx=10)

def print_month(event=None):
    print("Selected month:", month_combo.get())

month_combo.bind("<<ComboboxSelected>>", print_month)

# ----- Year Select -----

# Get current year and generate previous 4 years
current_year = datetime.now().year
years = [str(current_year - i) for i in range(5)]

year_combo = Combobox(monthbtn_frame, values=years, state="readonly")
year_combo.current(0)  # Set current year as default
year_combo.pack(side="left", padx=10)

def print_year(event=None):
    print("Selected year:", year_combo.get())

year_combo.bind("<<ComboboxSelected>>", print_year)

monthbtn = tk.Button(month_frame, text="Show This Months Mileage", command=show_mileage_month)
monthbtn.pack(side="left", padx=10)

yearbtn = tk.Button(month_frame, text="Show This Years Mileage", command=show_mileage_year)
yearbtn.pack(side="left", padx=10)

# Status label
status_label = tk.Label(root, text="", font=("Arial", 10), fg="red")
status_label.pack(pady=5)

# Current date field
current_date = datetime.now().strftime("%Y-%m-%d")
date_label = tk.Label(root, text=f"Current Date: {current_date}", font=("Arial", 10), fg="gray")
date_label.pack(side="bottom" ,pady=5)

root.mainloop()