from decimal import Decimal
import boto3
import json

def lambda_handler(event, context):
    print("Received event:")
    print(json.dumps(event))

    try:
        # Parse incoming JSON body from ESP32
        body = json.loads(event['body'])

        dev_id = body.get('dev_esp32', 'unknown')
        timestamp = body.get('timestamp', 'unknown')
        latitude = Decimal(str(body.get('latitude', 0.0)))
        longitude = Decimal(str(body.get('longitude', 0.0)))

        print(f"Parsed data: dev={dev_id}, time={timestamp}, lat={latitude}, lon={longitude}")

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('raw_data')

        response = table.put_item(
            Item={
                'dev_esp32': dev_id,
                'timestamp': timestamp,
                'latitude': latitude,
                'longitude': longitude
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Data inserted successfully'})
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to insert data'})
        }