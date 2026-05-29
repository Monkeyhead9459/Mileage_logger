import tkinter as tk
from tkinter import ttk
from logic.settings import save_settings


def open_settings_dialog(root, settings):
    """Open a modal settings dialog from the top-bar button."""
    dialog = tk.Toplevel(root)
    dialog.title("Settings")
    dialog.geometry("380x240")
    dialog.transient(root)
    dialog.grab_set()
    dialog.resizable(False, False)

    card = ttk.Frame(dialog, padding=20)
    card.pack(fill="both", expand=True)

    ttk.Label(card, text="Vehicle Settings", font=("Arial", 13, "bold")).grid(
        row=0, column=0, columnspan=2, pady=(0, 12))

    for row_idx, (label, key) in enumerate([
        ("Vehicle:",     "vehicle"),
        ("Designation:", "designation"),
        ("Categories:",  "categories"),
    ], start=1):
        ttk.Label(card, text=label, font=("Arial", 11)).grid(
            row=row_idx, column=0, sticky="e", padx=10, pady=4)
        entry = ttk.Entry(card, width=28)
        entry.insert(0, settings.get(key, ""))
        entry.grid(row=row_idx, column=1, sticky="w", pady=4)
        card.__dict__[f"_entry_{key}"] = entry

    def _save():
        data = {
            "vehicle":     card._entry_vehicle.get().strip(),
            "designation": card._entry_designation.get().strip(),
            "categories":  card._entry_categories.get().strip(),
        }
        save_settings(data)
        settings.update(data)
        dialog.destroy()

    ttk.Button(card, text="Save", command=_save).grid(
        row=4, column=0, columnspan=2, pady=16)

class SetupTab:
    def __init__(self, parent, settings):
        self.settings = settings
        self.frame = ttk.Frame(parent)
        self.build_ui()

    def build_ui(self):
        # Outer container to center the card
        container = ttk.Frame(self.frame)
        container.pack(expand=True, pady=40)

        # Card-style frame
        card = ttk.Frame(container, padding=20, relief="groove", borderwidth=2)
        card.grid(row=0, column=0)

        title = ttk.Label(card, text="Vehicle Settings", font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # --- Vehicle ---
        ttk.Label(card, text="Vehicle:", font=("Arial", 11)).grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.vehicle_entry = ttk.Entry(card, width=30)
        self.vehicle_entry.grid(row=1, column=1, sticky="w", pady=5)

        # --- Designation ---
        ttk.Label(card, text="Designation:", font=("Arial", 11)).grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.designation_entry = ttk.Entry(card, width=30)
        self.designation_entry.grid(row=2, column=1, sticky="w", pady=5)

        # --- Categories ---
        ttk.Label(card, text="Categories:", font=("Arial", 11)).grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.categories_entry = ttk.Entry(card, width=30)
        self.categories_entry.grid(row=3, column=1, sticky="w", pady=5)

        # Save button
        save_btn = ttk.Button(card, text="Save Settings", command=self.save)
        save_btn.grid(row=4, column=0, columnspan=2, pady=20)

        # Load existing settings into fields
        self.load_into_fields()

    def load_into_fields(self):
        """Populate entry fields from loaded settings."""
        self.vehicle_entry.delete(0, tk.END)
        self.vehicle_entry.insert(0, self.settings.get("vehicle", ""))

        self.designation_entry.delete(0, tk.END)
        self.designation_entry.insert(0, self.settings.get("designation", ""))

        self.categories_entry.delete(0, tk.END)
        self.categories_entry.insert(0, self.settings.get("categories", ""))

    def save(self):
        """Save settings to JSON file."""
        data = {
            "vehicle": self.vehicle_entry.get().strip(),
            "designation": self.designation_entry.get().strip(),
            "categories": self.categories_entry.get().strip(),
        }

        save_settings(data)

        # Update in-memory settings so other tabs see the new values
        self.settings.update(data)

        # Confirmation popup
        popup = tk.Toplevel(self.frame)
        popup.title("Saved")
        ttk.Label(popup, text="Settings saved successfully!", padding=20).pack()
        ttk.Button(popup, text="OK", command=popup.destroy).pack(pady=10)