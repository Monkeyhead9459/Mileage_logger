import boto3
from botocore.exceptions import BotoCoreError, ClientError
from boto3.dynamodb.conditions import Key
import csv
import os
import pytz   # install with: pip install pytz
import time
from collections import defaultdict
from datetime import datetime
from config import documents_folder
from logic.calculate import haversine

# Define your local timezone
LOCAL_TZ = pytz.timezone("Pacific/Auckland")

# -------------------------------
# Throttling for DynamoDB Free Tier
# -------------------------------
# Free tier: 25 read capacity units, 25 write capacity units
# Add delays to stay within limits
QUERY_DELAY = 0.1  # 100ms delay between queries
PAGINATION_DELAY = 0.2  # 200ms delay between pagination requests
BATCH_SIZE = 50  # Process items in smaller batches

# -------------------------------
# IAM Role Assumption Helper
# -------------------------------
ROLE_ARN = "arn:aws:iam::857687956870:role/RAP_ACCESS"   # <-- replace with your role ARN
SESSION_NAME = "MileageLoggerSession"

def assume_role():
    """Assume the IAM role and return temporary credentials."""
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName=SESSION_NAME
    )
    return response["Credentials"]

def get_dynamodb_resource():
    """Return a DynamoDB resource using temporary role credentials."""
    creds = assume_role()
    return boto3.resource(
        "dynamodb",
        region_name="ap-southeast-2",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"]
    )

# -------------------------------
# DynamoDB Table Setup
# -------------------------------
table_name = 'raw_data_v2'
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
    try:
        dt = datetime.fromisoformat(ts_str)
        dt_utc = pytz.UTC.localize(dt)
        dt_local = dt_utc.astimezone(LOCAL_TZ)
        return dt_local.isoformat()
    except ValueError as e:
        print(f"Warning: Invalid timestamp '{ts_str}': {e}")
        return ts_str  # Return original if conversion fails

def get_all_items(device="esp32_device_001"):
    try:
        # Step 1: Get DynamoDB table with role credentials
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)

        # Step 2: Get last saved timestamp
        last_saved = get_last_saved_timestamp(device, documents_folder)
        print(f"Latest saved timestamp for {device}: {last_saved}")

        # Step 3: Build query condition
        if last_saved:
            # Convert local timestamp to UTC for database comparison
            try:
                dt_local = datetime.fromisoformat(last_saved.replace('Z', '+00:00'))
                dt_utc = dt_local.astimezone(pytz.UTC)
                last_saved_utc = dt_utc.strftime('%Y-%m-%dT%H:%M:%S')
                key_condition = Key('dev_esp32').eq(device) & Key('timestamp').gt(last_saved_utc)
                print(f"Querying for items after: {last_saved_utc} (UTC)")
            except Exception as e:
                print(f"Error converting timestamp: {e}")
                key_condition = Key('dev_esp32').eq(device)
        else:
            key_condition = Key('dev_esp32').eq(device)

        # Step 4: Query DynamoDB with throttling
        items = []
        response = table.query(KeyConditionExpression=key_condition)
        initial_items = response.get('Items', [])
        items.extend(initial_items)
        
        print(f"Initial query returned {len(initial_items)} items")
        if initial_items:
            print(f"First item timestamp: {initial_items[0].get('timestamp', 'N/A')}")
            print(f"Last item timestamp: {initial_items[-1].get('timestamp', 'N/A')}")

        # Handle pagination with delays
        while 'LastEvaluatedKey' in response:
            time.sleep(PAGINATION_DELAY)  # Throttle pagination requests
            response = table.query(
                KeyConditionExpression=key_condition,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            new_items = response.get('Items', [])
            items.extend(new_items)
            print(f"Pagination: fetched {len(new_items)} more items")
            if new_items:
                print(f"  Batch range: {new_items[0].get('timestamp', 'N/A')} to {new_items[-1].get('timestamp', 'N/A')}")

        if not items:
            print("No new items found.")
            return

        print(f"Found {len(items)} NEW items for device '{device}'")

        # Step 5: Group new items by date
        grouped = defaultdict(list)
        valid_items = []
        for item in items:
            ts = item.get("timestamp", "")
            if not ts:
                continue

            local_ts = convert_timestamp_to_local(ts)
            if local_ts == ts:  # Conversion failed, skip this item
                continue
                
            item["timestamp"] = local_ts   # overwrite with local time

            date_part = local_ts[:10]      # group by local date
            
            # Validate date part (basic check for reasonable dates)
            try:
                year, month, day = map(int, date_part.split('-'))
                if not (2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31):
                    print(f"Skipping invalid date: {date_part}")
                    continue
            except:
                print(f"Skipping malformed date: {date_part}")
                continue
                
            grouped[date_part].append(item)
            valid_items.append(item)

        # Step 6: Append new data into per-date CSVs with batching
        for date, rows in grouped.items():
            csv_filename = f"{device}_{date}_output.csv"
            csv_path = os.path.join(documents_folder, csv_filename)

            file_exists = os.path.isfile(csv_path)
            with open(csv_path, mode='a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                
                # Write in batches to avoid overwhelming the file system
                for i in range(0, len(rows), BATCH_SIZE):
                    batch = rows[i:i + BATCH_SIZE]
                    writer.writerows(batch)
                    if i + BATCH_SIZE < len(rows):  # Add delay between batches
                        time.sleep(0.05)  # 50ms delay between batches

            print(f"Appended {len(rows)} rows to {csv_path}")
            time.sleep(QUERY_DELAY)  # Delay between processing different files

        # Step 7: Update tracker file with newest timestamp (only from valid items)
        if valid_items:
            latest_ts = max(item["timestamp"] for item in valid_items if "timestamp" in item)
            update_last_saved_timestamp(device, documents_folder, latest_ts)
            print(f"Updated last saved timestamp: {latest_ts}")
        else:
            print("No valid items to update timestamp")

    except (BotoCoreError, ClientError) as error:
        print(f"Error: {error}")

if __name__ == "__main__":
    get_all_items()