import tkinter as tk
from tkinter import Label
from datetime import datetime
import webbrowser
from tkcalendar import DateEntry
from tkinter.ttk import Combobox

def greet():
    Label.config(text="Mileage is .... km")

def show_map():
    try:
        lat = float(lat_entry.get())
        lon = float(lon_entry.get())
        url = f"https://www.google.com/maps?q={lat},{lon}"
        webbrowser.open(url)
    except ValueError:
        Label.config(text="Invalid latitude or longitude")

def print_date():
    selected = cal.get_date()
    print(f"Selected date: {selected}")

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

# Optional: bind to a function or use a button
cal.bind("<<DateEntrySelected>>", lambda e: print_date())

daybtn = tk.Button(day_frame, text="Show This Days Mileage", command=greet)
daybtn.pack(side="left", padx=10)

mapbtn = tk.Button(day_frame, text="Show Map", command=show_map)
mapbtn.pack(side="left", padx=10)


#tk.Label(root, text="Latitude:").pack()
#lat_entry = tk.Entry(root)
#lat_entry.pack()

#tk.Label(root, text="Longitude:").pack()
#lon_entry = tk.Entry(root)
#lon_entry.pack()

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

monthbtn = tk.Button(month_frame, text="Show This Months Mileage", command=greet)
monthbtn.pack(pady=5)



# Current date field
current_date = datetime.now().strftime("%Y-%m-%d")
date_label = tk.Label(root, text=f"Current Date: {current_date}", font=("Arial", 10), fg="gray")
date_label.pack(side="bottom" ,pady=5)

root.mainloop()