# config.py
import os, sys

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

documents_folder = os.path.join(base_path, "Outputs")
os.makedirs(documents_folder, exist_ok=True)

filtered_folder = os.path.join(base_path, "Outputs_Filtered")
os.makedirs(filtered_folder, exist_ok=True)

backups_folder = os.path.join(base_path, "Merge_Backups")
os.makedirs(backups_folder, exist_ok=True)

APP_VERSION = "v1.0.2"