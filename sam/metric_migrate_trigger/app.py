import json
import logging
from datetime import datetime
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CLOUDWATCH_STATISTICS = ["Average", "Minimum", "Maximum", "Sum", "SampleCount", "IQM", "p99", "tm99", "tc99", "ts99"]

def validate_request(body):
    """Validate the request body"""
    required_fields = ['namespace', 'metricName', 'dimensions', 'startTime', 'endTime', 'destinationMetricName', 'destinationKey', 'cloudwatchStats']
    
    for field in required_fields:
        if field not in body:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate dimensions format
    if not isinstance(body['dimensions'], list):
        raise ValueError("Dimensions must be a list")
    
    # Validate time format
    try:
        datetime.fromisoformat(body['startTime'].replace('Z', '+00:00'))
        datetime.fromisoformat(body['endTime'].replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid time format. Use ISO 8601 format (e.g., 2024-01-01T00:00:00Z)")
    
    # Validate that cloudwatch stats are valid

    if not isinstance(body['cloudwatchStats'], list):
        raise ValueError("cloudwatchStats must be a list")
    
    if len(body['cloudwatchStats']) == 0:
        raise ValueError(f"cloudwatchStats must include at least one statistic to migrate. Valid stats are {json.dumps(CLOUDWATCH_STATISTICS)}")

    for cwStat in body['cloudwatchStats']:
        if cwStat not in CLOUDWATCH_STATISTICS:
            raise ValueError(f"{cwStat} is not a valid cloudwatch stat. Valid stats are {json.dumps(CLOUDWATCH_STATISTICS)}")

def lambda_handler(event, context):
    """
    Handle metric query requests
    
    Expected request body:
    {
        "namespace": "AWS/Lambda",
        "metricName": "Invocations",
        "dimensions": [
            {
                "Name": "FunctionName",
                "Value": "MyFunction"
            }
        ],
        "startTime": "2024-01-01T00:00:00Z",
        "endTime": "2024-01-02T00:00:00Z",
        "period": 300,
        "statistic": "Sum"
    }
    """
    try:
        # Parse request body
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        
        # Validate request
        validate_request(body)
        
        # Log the request
        logger.info(f"Processing metric query: {json.dumps(body)}")
        
        # Write the request to an SQS queue
        sqs_client = boto3.client('sqs')
        queue_url = os.environ['MIGRATION_QUEUE_URL'] 
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))
        logger.info(f"Request sent to SQS: {json.dumps(body)}")


        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'request': body,
                'message': 'Query request received successfully'
            })
        }
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Validation Error',
                'message': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }
