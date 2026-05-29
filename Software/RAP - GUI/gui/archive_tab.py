import tkinter as tk
from tkinter import ttk

from logic import journey_loader
from gui.map_window import MapWindow


class ArchiveTab:
    def __init__(self, parent, settings, deleted):
        self.settings = settings
        self.deleted = deleted
        self.frame = ttk.Frame(parent)

        self.selected_journeys = {}

        self.build_ui()

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def build_ui(self):
        # --- Buttons ---
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Load Archived Journeys", command=self.load_archived).pack(side="left", padx=5)

        # --- Table ---
        ttk.Label(self.frame, text="Archived Journeys:", font=("Arial", 12)).pack(pady=10)

        self.table = ttk.Treeview(
            self.frame,
            columns=("check", "date", "journey", "start", "end", "duration", "distance"),
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
            ("distance", "Distance (km)", 120),
        ]:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center")

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

        ttk.Button(bottom, text="Show on Map", command=self.show_on_map).pack(side="left", padx=10)
        ttk.Button(bottom, text="Mileage (Selected)", command=self.mileage_selected).pack(side="left", padx=10)
        ttk.Button(bottom, text="Unarchive Selected", command=self.unarchive_selected).pack(side="left", padx=10)

        # Status label
        self.status = ttk.Label(self.frame, text="", foreground="red")
        self.status.pack(pady=5)

    # ------------------------------------------------------------
    # LOAD ARCHIVED JOURNEYS
    # ------------------------------------------------------------
    def load_archived(self):
        for row in self.table.get_children():
            self.table.delete(row)

        self.selected_journeys.clear()
        self.select_all_var.set(False)

        if not self.deleted.data:
            self.status.config(text="No archived journeys found")
            return

        for date in sorted(self.deleted.data.keys()):
            journeys = journey_loader.load_archived_day(date, self.deleted)

            for j in journeys:
                jid = j["journey_id"]
                key = f"{date}:{jid}"
                self.selected_journeys[key] = False

                start_time = j["start_time"].split("T")[1].split("+")[0]
                end_time = j["end_time"].split("T")[1].split("+")[0]

                self.table.insert(
                    "",
                    "end",
                    values=(
                        "",
                        date,
                        jid,
                        start_time,
                        end_time,
                        j["duration"],
                        f"{j['distance']:.2f}"
                    )
                )

        count = len(self.selected_journeys)
        self.status.config(
            text=f"Loaded {count} archived journey(s)",
            foreground="green"
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

        date = self.table.set(row_id, "date")
        jid = self.table.set(row_id, "journey")
        key = f"{date}:{jid}"

        self.selected_journeys[key] = not self.selected_journeys[key]
        self.table.set(row_id, "check", "✓" if self.selected_journeys[key] else "")

    def toggle_select_all(self):
        select_all = self.select_all_var.get()
        for row_id in self.table.get_children():
            date = self.table.set(row_id, "date")
            jid = self.table.set(row_id, "journey")
            key = f"{date}:{jid}"
            self.selected_journeys[key] = select_all
            self.table.set(row_id, "check", "✓" if select_all else "")

    # ------------------------------------------------------------
    # MAP DISPLAY
    # ------------------------------------------------------------
    def show_on_map(self):
        selected = {}

        for row_id in self.table.get_children():
            date = self.table.set(row_id, "date")
            jid = int(self.table.set(row_id, "journey"))
            key = f"{date}:{jid}"

            if self.selected_journeys.get(key, False):
                selected.setdefault(date, [])
                selected[date].append(jid)

        if not selected:
            self.status.config(text="No journeys selected")
            return

        coords = {}
        for date, ids in selected.items():
            coords.update(journey_loader.get_coords(date, ids))

        MapWindow(self.frame, coords)

    # ------------------------------------------------------------
    # MILEAGE
    # ------------------------------------------------------------
    def mileage_selected(self):
        total = 0.0
        for row_id in self.table.get_children():
            date = self.table.set(row_id, "date")
            jid = self.table.set(row_id, "journey")
            key = f"{date}:{jid}"

            if self.selected_journeys.get(key, False):
                total += float(self.table.set(row_id, "distance"))

        if total == 0:
            self.status.config(text="No journeys selected")
        else:
            self.status.config(text=f"Selected mileage: {total:.2f} km", foreground="green")

    # ------------------------------------------------------------
    # UNARCHIVE
    # ------------------------------------------------------------
    def unarchive_selected(self):
        selected = {}

        for row_id in self.table.get_children():
            date = self.table.set(row_id, "date")
            jid = int(self.table.set(row_id, "journey"))
            key = f"{date}:{jid}"

            if self.selected_journeys.get(key, False):
                selected.setdefault(date, [])
                selected[date].append(jid)

        if not selected:
            self.status.config(text="No journeys selected")
            return

        for date, ids in selected.items():
            self.deleted.unarchive(date, ids)

        self.load_archived()
        self.status.config(text="Selected journeys unarchived", foreground="green")
