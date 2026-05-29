import os
import shutil
import tkinter as tk
from tkinter import ttk

from logic.merge_history import MergeHistory
from logic import journey_loader
from gui.map_window import MapWindow
from config import filtered_folder


class MergesTab:
    def __init__(self, parent, settings, deleted):
        self.settings = settings
        self.deleted = deleted
        self.history = MergeHistory()
        self.frame = ttk.Frame(parent)
        self.build_ui()

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def build_ui(self):
        ttk.Label(self.frame, text="Merge History", font=("Arial", 13, "bold")).pack(pady=(12, 4))
        ttk.Label(
            self.frame,
            text="Select a merge below and click Revert to restore the original journeys.",
            foreground="gray"
        ).pack(pady=(0, 8))

        # Table
        cols = ("date", "original", "merged_to", "time", "folder")
        self.table = ttk.Treeview(
            self.frame, columns=cols, show="headings", selectmode="browse", height=16
        )
        self.table.heading("date", text="Date")
        self.table.heading("original", text="Original Journey IDs")
        self.table.heading("merged_to", text="Merged To")
        self.table.heading("time", text="Merge Time")
        self.table.heading("folder", text="Data Source")

        self.table.column("date", width=110, anchor="center")
        self.table.column("original", width=180, anchor="center")
        self.table.column("merged_to", width=100, anchor="center")
        self.table.column("time", width=160, anchor="center")
        self.table.column("folder", width=100, anchor="center")

        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)

        self.table.pack(side="left", fill="both", expand=True, padx=(10, 0))
        scrollbar.pack(side="left", fill="y", pady=5)

        # Buttons
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(side="right", padx=10, pady=10, anchor="n")

        ttk.Button(btn_frame, text="Refresh", command=self.load_history).pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="Show on Map", command=self.show_on_map).pack(pady=5, fill="x")
        ttk.Button(btn_frame, text="Revert Selected", command=self.revert_selected).pack(pady=5, fill="x")

        self.status = ttk.Label(self.frame, text="", foreground="red")
        self.status.pack(side="bottom", pady=8)

        self.load_history()

    # ------------------------------------------------------------
    # DATA
    # ------------------------------------------------------------
    def load_history(self):
        self.table.delete(*self.table.get_children())
        self.history = MergeHistory()
        entries = sorted(self.history.all(), key=lambda e: e.get("merge_time", ""), reverse=True)
        for entry in entries:
            orig = ", ".join(str(j) for j in entry.get("original_jids", []))
            self.table.insert("", "end", iid=entry["id"], values=(
                entry.get("date", ""),
                orig,
                entry.get("merged_jid", ""),
                entry.get("merge_time", ""),
                entry.get("folder", ""),
            ))

    # ------------------------------------------------------------
    # MAP
    # ------------------------------------------------------------
    def show_on_map(self):
        selected = self.table.selection()
        if not selected:
            self.status.config(text="Select a merge to show on map", foreground="red")
            return

        merge_id = selected[0]
        entry = next((e for e in self.history.all() if e.get("id") == merge_id), None)
        if not entry:
            self.status.config(text="Merge record not found", foreground="red")
            return

        date = entry.get("date", "")
        merged_jid = entry.get("merged_jid")
        if not date or merged_jid is None:
            self.status.config(text="Missing date or journey ID in record", foreground="red")
            return

        coords = journey_loader.get_coords(date, [int(merged_jid)], folder=filtered_folder)
        if not any(coords.values()):
            self.status.config(text="No coordinates found for this journey", foreground="red")
            return

        MapWindow(self.frame, coords)
        self.status.config(text="", foreground="red")

    # ------------------------------------------------------------
    # REVERT
    # ------------------------------------------------------------
    def revert_selected(self):
        selected = self.table.selection()
        if not selected:
            self.status.config(text="Select a merge to revert", foreground="red")
            return

        merge_id = selected[0]
        entry = next((e for e in self.history.all() if e.get("id") == merge_id), None)
        if not entry:
            self.status.config(text="Merge record not found", foreground="red")
            return

        backup_path = entry.get("backup_path", "")
        csv_path = entry.get("csv_path", "")

        if not os.path.exists(backup_path):
            self.status.config(text=f"Backup file not found: {backup_path}", foreground="red")
            return

        if not csv_path:
            self.status.config(text="CSV path not recorded in history", foreground="red")
            return

        try:
            shutil.copy2(backup_path, csv_path)
            os.remove(backup_path)
        except OSError as e:
            self.status.config(text=f"Revert failed: {e}", foreground="red")
            return

        self.history.remove(merge_id)
        self.load_history()
        orig = ", ".join(str(j) for j in entry.get("original_jids", []))
        self.status.config(
            text=f"Reverted: {entry['date']} journeys {orig} restored",
            foreground="green"
        )
