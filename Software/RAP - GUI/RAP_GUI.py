import tkinter as tk
from tkinter import ttk

from gui.setup_tab import open_settings_dialog
from gui.single_day_tab import SingleDayTab
from gui.range_tab import RangeTab
from gui.merges_tab import MergesTab
from gui.drift_removed_tab import DriftRemovedTab
from gui.archive_tab import ArchiveTab

from logic.settings import load_settings
from logic.soft_delete import DeletedJourneys
from logic.journey import assign_daily_journey_ids
from logic.db_pull import get_all_items
from logic.filter_runner import run_filter
from config import documents_folder, filtered_folder

from updater import auto_update


def main():
    # Optional: auto-update logic
    try:
        auto_update()
    except Exception:
        pass

    # Pull latest data from database
    try:
        get_all_items()
    except Exception:
        pass

    # Ensure all CSV files have proper journey IDs
    try:
        assign_daily_journey_ids(documents_folder)
    except Exception:
        pass

    # Generate filtered versions of all output files
    try:
        run_filter()
    except Exception:
        pass

    root = tk.Tk()
    root.title("Remote Access Program")
    root.geometry("1100x750")

    # --- Top bar with settings button ---
    header = tk.Frame(root, relief="flat", bd=0)
    header.pack(side="top", fill="x")

    # Shared state (needs to exist before the button lambda)
    settings = load_settings()
    deleted = DeletedJourneys()

    ttk.Button(
        header, text="⚙ Settings",
        command=lambda: open_settings_dialog(root, settings)
    ).pack(side="right", padx=8, pady=4)

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    # --- Always-visible tabs ---
    single_day_tab = SingleDayTab(notebook, settings, deleted)
    range_tab      = RangeTab(notebook, settings, deleted)

    notebook.add(single_day_tab.frame, text="Single Day")
    notebook.add(range_tab.frame,      text="Date Range")

    # --- Debug-only tabs (hidden until Ctrl+D) ---
    archive_tab   = ArchiveTab(notebook, settings, deleted)
    raw_day_tab   = SingleDayTab(notebook, settings, deleted, folder=documents_folder)
    merges_tab    = MergesTab(notebook, settings, deleted)
    drift_tab     = DriftRemovedTab(notebook, settings, deleted)
    debug_tabs = [
        (archive_tab.frame,  "Archive"),
        (raw_day_tab.frame,  "Raw Data"),
        (merges_tab.frame,   "Merge History"),
        (drift_tab.frame,    "Drift Removed"),
    ]

    # --- Debug mode toggle (Ctrl+D) ---
    debug_mode = {"on": False}

    def toggle_debug(event=None):
        if debug_mode["on"]:
            for frame, _ in debug_tabs:
                try:
                    notebook.forget(frame)
                except tk.TclError:
                    pass
            single_day_tab.set_debug_columns(False)
            range_tab.set_debug_columns(False)
            root.title("Remote Access Program")
            debug_mode["on"] = False
        else:
            for frame, label in debug_tabs:
                notebook.add(frame, text=label)
            single_day_tab.set_debug_columns(True)
            range_tab.set_debug_columns(True)
            root.title("Remote Access Program [DEBUG]")
            debug_mode["on"] = True

    root.bind("<Control-d>", toggle_debug)

    root.mainloop()


if __name__ == "__main__":
    main()