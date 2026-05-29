import tkinter as tk
from tkinter import ttk

from logic.gap_fill_log import GapFillLog
from logic import journey_loader
from config import filtered_folder
from gui.map_window import MapWindow


class GapFillTab:
    def __init__(self, parent, settings):
        self.settings = settings
        self.frame = ttk.Frame(parent)
        self.log = GapFillLog()
        self.build_ui()

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def build_ui(self):
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Refresh", command=self.load_log).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Show on Map", command=self.show_on_map).pack(side="left", padx=5)

        ttk.Label(self.frame, text="Road Gap-Filled Journeys:", font=("Arial", 12)).pack(pady=10)

        self.table = ttk.Treeview(
            self.frame,
            columns=("date", "journey", "gaps_filled", "points_added"),
            show="headings",
            height=16,
        )

        for col, text, width in [
            ("date",         "Date",          120),
            ("journey",      "Journey",        70),
            ("gaps_filled",  "Gaps Filled",   100),
            ("points_added", "Points Added",  110),
        ]:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor="center")

        self.table.pack(pady=10, fill="x")

        self.status = ttk.Label(self.frame, text="", foreground="red")
        self.status.pack(pady=5)

        self.load_log()

    # ------------------------------------------------------------
    # LOAD LOG
    # ------------------------------------------------------------
    def load_log(self):
        for row in self.table.get_children():
            self.table.delete(row)

        self.log = GapFillLog()
        entries = self.log.all()

        if not entries:
            self.status.config(text="No gap-fill records found", foreground="grey")
            return

        for entry in entries:
            self.table.insert(
                "", "end",
                iid=f"{entry['date']}:{entry['journey_id']}",
                values=(
                    entry["date"],
                    entry["journey_id"],
                    entry["gaps_filled"],
                    entry["points_added"],
                ),
            )

        self.status.config(text=f"Loaded {len(entries)} record(s)", foreground="green")

    # ------------------------------------------------------------
    # MAP DISPLAY
    # ------------------------------------------------------------
    def show_on_map(self):
        selected = self.table.selection()
        if not selected:
            self.status.config(text="Select a row to show on map", foreground="red")
            return

        iid = selected[0]
        date, jid_str = iid.split(":", 1)

        try:
            jid = int(jid_str)
        except ValueError:
            self.status.config(text="Invalid journey ID", foreground="red")
            return

        coords = journey_loader.get_coords(date, [jid], folder=filtered_folder)
        if not any(coords.values()):
            self.status.config(text="No coordinates found for this journey", foreground="red")
            return

        MapWindow(self.frame, coords)
        self.status.config(text="", foreground="red")
