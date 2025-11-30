# config.py
import os, sys

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

documents_folder = os.path.join(base_path, "Outputs")
os.makedirs(documents_folder, exist_ok=True)