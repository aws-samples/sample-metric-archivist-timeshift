import json
import boto3
import os
import logging

lambda_client = boto3.client('lambda')

target_lambda = os.environ['S3_CSV_LOADING_LAMBDA_ARN']

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    logging.error(f"Received event {event}")

    if 'EventType' not in event:
        raise RuntimeError("EventType missing from event")
    
    eventType = event['EventType']

    match eventType:
        case 'GetMetricData':
            return handleGetMetricData(event, context)
        case 'DescribeGetMetricData':
            return handleDescribeGetMetricData(event, context)
        case _:
            raise RuntimeError('Invalid EventType')
    
def handleDescribeGetMetricData(event, context):
    description = """
## Timeshift a metric that's loaded from a CSV in S3.

### Query Arguments
ArgNumber | Type | Description
---|---|---
1 | String | S3 Bucket Name (not ARN or URL - just the name)
2 | String | S3 Key Name (may include slashes)
    """
    argDefaults = [{"Value": "sam-archivedmetricss3bucket-o8rfmx9plemb"},{"Value": "test-key-01"}]
    dataSourceConnectorName = "sam-TimeshiftLambda-1eWG0Ss7miVE"

    return {
        "DataSourceConnectorName": dataSourceConnectorName,
        "ArgumentDefaults": argDefaults,
        "Description": description
    }


def handleGetMetricData(event, context):
    try:
        logger.error("Starting handleGetMetricData")
        # Invoke the S3CloudWatchDataSourceLambda
        response = lambda_client.invoke(
            FunctionName=target_lambda,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(event)  # Pass through the original event
        )
        logger.error(f"Response from source lambda {response}")
    except Exception as e:
        logger.error(f"Exception while calling source lambda {e}")
        return {
            'statusCode': 500,
            'body': f'Error invoking S3CloudWatchDataSourceLambda: {str(e)}'
        }
    
    # Read the response payload
    response_payload = json.loads(response['Payload'].read().decode('utf-8'))
    
    return response_payload