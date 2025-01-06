import json
import boto3
import os
import logging
import isodate

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
3 | String | an ISO 8601 duration string by which all data should be shifted forward.

### ISO 8601 example duration strings

Input String | resulting duration
---|---
P2W | two weeks
P2D | two days
P2W2D | two weeks + two days
PT1M | one minute
P1DT1H | one day + one hour
P1DT1M | one day + one minute
"""
    argDefaults = [{"Value": "sam-archivedmetricss3bucket-o8rfmx9plemb"},{"Value": "test-key-01"},{"Value":"P0D"}]
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
        durationString = event['GetMetricDataRequest']['Arguments'][2]
        logger.info(f"Duration string from event {durationString}")
        duration = isodate.parse_duration(durationString)
        logger.info(f"Duration {duration} is type {type(duration)}")

        del event['GetMetricDataRequest']['Arguments'][2]
        
        logger.info(f"Event with argument(s) removed {event}")
        response = lambda_client.invoke(
            FunctionName=target_lambda,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(event)  # Pass through the original event, with only the first two arguments
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
    for result in response_payload['MetricDataResults']:
        origTimestamps = result['Timestamps']
        newTimestamps = [None] * len(origTimestamps)
        for i in range(0, len(origTimestamps)):
            origTime = origTimestamps[i]
            newTimestamps[i] = int(origTime + duration.total_seconds())
            logger.error(f"origTime is of class {type(origTime)}")
        logger.info(f"Swapping timestamps: {origTimestamps} into the shifted {newTimestamps}")
        result['Timestamps'] = newTimestamps

    logger.info(f"Returning {response_payload} from handleGetMetricData")
    return response_payload