import os
import csv
from config import documents_folder, filtered_folder
from logic.gps_filter import filter_rows
from logic.journey_merge import run_auto_merge


def run_filter():
    """
    Read all *_output.csv files from documents_folder,
    apply GPS drift filters, and write results to filtered_folder.
    Re-processes a file if:
      - the raw CSV is newer than the filtered CSV, OR
      - gps_filter.py is newer than the filtered CSV (filter logic changed).
    """
    csv_files = [f for f in os.listdir(documents_folder) if f.endswith("_output.csv")]

    if not csv_files:
        print("No output CSV files to filter.")
        return

    # If gps_filter.py was modified more recently than a filtered file,
    # that filtered file must be regenerated regardless of raw data age.
    _filter_logic_path = os.path.join(os.path.dirname(__file__), "gps_filter.py")
    _filter_logic_mtime = os.path.getmtime(_filter_logic_path) if os.path.exists(_filter_logic_path) else 0

    processed = 0
    for filename in csv_files:
        raw_path = os.path.join(documents_folder, filename)
        filtered_path = os.path.join(filtered_folder, filename)

        # Skip if filtered file is up-to-date AND has actual data rows
        if os.path.exists(filtered_path):
            filtered_mtime = os.path.getmtime(filtered_path)
            if filtered_mtime >= os.path.getmtime(raw_path) and filtered_mtime >= _filter_logic_mtime:
                with open(filtered_path, newline="") as check_f:
                    check_reader = csv.DictReader(check_f)
                    has_data = any(True for _ in check_reader)
                if has_data:
                    continue
                # Empty filtered file — delete it and don't re-process
                os.remove(filtered_path)
                continue

        try:
            with open(raw_path, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                fieldnames = reader.fieldnames

            if not rows or not fieldnames:
                continue

            filtered = filter_rows(rows)

            if not filtered:
                # All rows removed — delete the filtered file if it exists so
                # the date doesn't appear in dropdowns when using filtered mode
                if os.path.exists(filtered_path):
                    os.remove(filtered_path)
                print(f"Filtered {filename}: {len(rows)} -> 0 rows (file removed)")
                continue

            with open(filtered_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(filtered)

            print(f"Filtered {filename}: {len(rows)} -> {len(filtered)} rows")
            processed += 1

        except Exception as e:
            print(f"Error filtering {filename}: {e}")

    if processed:
        print(f"Filter complete: {processed} file(s) updated")
    else:
        print("All filtered files are up-to-date")

    run_auto_merge(filtered_folder)
