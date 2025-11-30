import boto3
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key
import csv
import os
import pytz   # install with: pip install pytz
from collections import defaultdict
from config import documents_folder

# Define your local timezone
LOCAL_TZ = pytz.timezone("Pacific/Auckland")


# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-2')
table_name = 'raw_data_v2'
table = dynamodb.Table(table_name)
fieldnames = ['dev_esp32', 'timestamp', 'altitude', 'latitude', 'longitude']

def get_last_saved_timestamp(device, documents_folder):
    """Read last saved timestamp from device-specific tracker CSV."""
    tracker_file = os.path.join(documents_folder, f"{device}_last_timestamp.csv")
    if os.path.isfile(tracker_file):
        with open(tracker_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                return row.get("last_timestamp")  # only one row expected
    return None

def update_last_saved_timestamp(device, documents_folder, latest_ts):
    """Update tracker CSV with new last saved timestamp."""
    tracker_file = os.path.join(documents_folder, f"{device}_last_timestamp.csv")
    with open(tracker_file, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["last_timestamp"])
        writer.writeheader()
        writer.writerow({"last_timestamp": latest_ts})

        
def convert_timestamp_to_local(ts_str):
    """
    Convert GPS UTC timestamp string (ISO 8601) to local timezone string.
    Example input: '2025-10-09T01:07:39'
    """
    # Parse as naive datetime
    dt = datetime.fromisoformat(ts_str)

    # Attach UTC timezone
    dt_utc = pytz.UTC.localize(dt)

    # Convert to local timezone
    dt_local = dt_utc.astimezone(LOCAL_TZ)

    # Return as ISO string (or any format you prefer)
    return dt_local.isoformat()


def get_all_items(device="esp32_device_001"):
    try:
        
        # Step 1: Get last saved timestamp
        last_saved = get_last_saved_timestamp(device, documents_folder)
        print(f"Latest saved timestamp for {device}: {last_saved}")

        # Step 2: Build query condition
        if last_saved:
            key_condition = Key('dev_esp32').eq(device) & Key('timestamp').gt(last_saved)
        else:
            key_condition = Key('dev_esp32').eq(device)

        # Step 3: Query DynamoDB
        items = []
        response = table.query(KeyConditionExpression=key_condition)
        items.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression=key_condition,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        if not items:
            print("No new items found.")
            return

        print(f"Found {len(items)} NEW items for device '{device}'")

        # Step 4: Group new items by date
        grouped = defaultdict(list)
        for item in items:
            ts = item.get("timestamp", "")
            if not ts:
                continue

            # Convert UTC 
            local_ts = convert_timestamp_to_local(ts)
            item["timestamp"] = local_ts   # overwrite with local time

            date_part = local_ts[:10]      # group by local date
            grouped[date_part].append(item)


        # Step 5: Append new data into per-date CSVs
        for date, rows in grouped.items():
            csv_filename = f"{device}_{date}_output.csv"
            csv_path = os.path.join(documents_folder, csv_filename)

            file_exists = os.path.isfile(csv_path)
            with open(csv_path, mode='a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(rows)

            print(f"Appended {len(rows)} rows → {csv_path}")

        # Step 6: Update tracker file with newest timestamp
        latest_ts = max(item["timestamp"] for item in items if "timestamp" in item)
        update_last_saved_timestamp(device, documents_folder, latest_ts)
        print(f"Updated last saved timestamp: {latest_ts}")

    except (BotoCoreError, ClientError) as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    get_all_items()