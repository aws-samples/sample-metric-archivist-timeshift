# Copyright 2026 Amazon.com and its affiliates; all rights reserved.
# This file is Amazon Web Services Content and may not be duplicated or distributed without permission.

import json
import boto3
import os
import logging
import isodate

# Set up logging FIRST before any other operations
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logger.info("Timeshift Lambda initializing...")
logger.info(f"Available environment variables: {list(os.environ.keys())}")

lambda_client = boto3.client('lambda')

# Check if the required environment variable exists
if 'S3_CSV_LOADING_LAMBDA_ARN' not in os.environ:
    logger.error("CRITICAL: S3_CSV_LOADING_LAMBDA_ARN environment variable is not set!")  # nosemgrep: logging-error-without-handling
    logger.error(f"Available environment variables: {json.dumps(dict(os.environ), indent=2)}")  # nosemgrep: logging-error-without-handling
    error_msg = """
    S3_CSV_LOADING_LAMBDA_ARN environment variable is required but not set.
    
    This Lambda function requires an S3 CSV Data Source to be configured in CloudWatch.
    
    To set this up:
    1. Follow the instructions at: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Metrics-Insights-datasources-S3.html
    2. After creating the S3 CSV Data Source, find the Lambda ARN in the CloudWatch console
    3. Deploy this stack with the S3CsvLoadingLambdaArn parameter set to that ARN
    
    Example:
    sam deploy --parameter-overrides S3CsvLoadingLambdaArn=arn:aws:lambda:us-east-1:123456789012:function:your-s3-csv-function
    """
    logger.error(error_msg)  # nosemgrep: logging-error-without-handling
    raise RuntimeError(error_msg)

target_lambda = os.environ['S3_CSV_LOADING_LAMBDA_ARN']
logger.info(f"Target Lambda ARN: {target_lambda}")

def lambda_handler(event, context):
    logger.info("=== Lambda Handler Invoked ===")
    logger.info(f"Event type: {type(event)}")
    logger.info(f"Full event: {json.dumps(event, default=str, indent=2)}")
    logger.info(f"Context: {context}")
    
    try:
        if 'EventType' not in event:
            logger.error("EventType missing from event")  # nosemgrep: logging-error-without-handling
            logger.error(f"Event keys present: {list(event.keys())}")  # nosemgrep: logging-error-without-handling
            raise RuntimeError("EventType missing from event")
        
        eventType = event['EventType']
        logger.info(f"Processing EventType: {eventType}")

        match eventType:
            case 'GetMetricData':
                return handleGetMetricData(event, context)
            case 'DescribeGetMetricData':
                return handleDescribeGetMetricData(event, context)
            case _:
                logger.error(f"Invalid EventType received: {eventType}")  # nosemgrep: logging-error-without-handling
                raise RuntimeError(f'Invalid EventType: {eventType}')
    except Exception as e:
        logger.error(f"Exception in lambda_handler: {str(e)}", exc_info=True)  # nosemgrep: logging-error-without-handling
        raise
    
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
        logger.info("=== Starting handleGetMetricData ===")
        logger.info(f"Event structure: {json.dumps(event, default=str, indent=2)}")
        
        # Validate event structure
        if 'GetMetricDataRequest' not in event:
            logger.error("GetMetricDataRequest missing from event")  # nosemgrep: logging-error-without-handling
            raise RuntimeError("GetMetricDataRequest missing from event")
        
        if 'Arguments' not in event['GetMetricDataRequest']:
            logger.error("Arguments missing from GetMetricDataRequest")  # nosemgrep: logging-error-without-handling
            raise RuntimeError("Arguments missing from GetMetricDataRequest")
        
        arguments = event['GetMetricDataRequest']['Arguments']
        logger.info(f"Arguments received: {arguments}")
        logger.info(f"Number of arguments: {len(arguments)}")
        
        if len(arguments) < 3:
            logger.error(f"Expected at least 3 arguments, got {len(arguments)}")  # nosemgrep: logging-error-without-handling
            raise RuntimeError(f"Expected at least 3 arguments (bucket, key, duration), got {len(arguments)}")
        
        # Invoke the S3CloudWatchDataSourceLambda
        durationString = arguments[2]
        logger.info(f"Duration string from event: {durationString}")
        
        try:
            duration = isodate.parse_duration(durationString)
            logger.info(f"Parsed duration: {duration} (type: {type(duration)})")
        except Exception as e:
            logger.error(f"Failed to parse duration string '{durationString}': {str(e)}")  # nosemgrep: logging-error-without-handling
            raise RuntimeError(f"Invalid ISO 8601 duration string: {durationString}")

        # Remove the duration argument before passing to target lambda
        del event['GetMetricDataRequest']['Arguments'][2]
        
        logger.info(f"Event after removing duration argument: {json.dumps(event, default=str, indent=2)}")
        logger.info(f"Invoking target lambda: {target_lambda}")
        
        response = lambda_client.invoke(
            FunctionName=target_lambda,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(event)  # Pass through the original event, with only the first two arguments
        )
        logger.info(f"Lambda invoke response status: {response['StatusCode']}")
        logger.info(f"Response metadata: {json.dumps({k: v for k, v in response.items() if k != 'Payload'}, default=str)}")
        
    except Exception as e:
        logger.error(f"Exception while calling source lambda: {str(e)}", exc_info=True)  # nosemgrep: logging-error-without-handling
        return {
            'statusCode': 500,
            'body': f'Error invoking S3CloudWatchDataSourceLambda: {str(e)}'
        }

    # Read the response payload
    try:
        payload_bytes = response['Payload'].read()
        logger.info(f"Payload size: {len(payload_bytes)} bytes")
        response_payload = json.loads(payload_bytes.decode('utf-8'))
        logger.info(f"Response payload structure: {json.dumps({k: type(v).__name__ for k, v in response_payload.items()})}")
    except Exception as e:
        logger.error(f"Failed to parse response payload: {str(e)}", exc_info=True)  # nosemgrep: logging-error-without-handling
        raise
    
    # Time-shift the timestamps
    try:
        if 'MetricDataResults' not in response_payload:
            logger.error("MetricDataResults missing from response payload")  # nosemgrep: logging-error-without-handling
            logger.error(f"Response payload keys: {list(response_payload.keys())}")  # nosemgrep: logging-error-without-handling
            raise RuntimeError("MetricDataResults missing from response")
        
        for idx, result in enumerate(response_payload['MetricDataResults']):
            logger.info(f"Processing result {idx}: {result.get('Id', 'unknown')}")
            
            if 'Timestamps' not in result:
                logger.warning(f"Result {idx} has no Timestamps field")
                continue
            
            origTimestamps = result['Timestamps']
            logger.info(f"Original timestamps count: {len(origTimestamps)}")
            
            newTimestamps = []
            for i, origTime in enumerate(origTimestamps):
                logger.debug(f"Original timestamp {i}: {origTime} (type: {type(origTime)})")
                newTime = int(origTime + duration.total_seconds())
                newTimestamps.append(newTime)
                if i < 3:  # Log first 3 for debugging
                    logger.info(f"Timestamp {i}: {origTime} -> {newTime} (shifted by {duration.total_seconds()}s)")
            
            result['Timestamps'] = newTimestamps
            logger.info(f"Result {idx} timestamps shifted successfully")

        logger.info("=== handleGetMetricData completed successfully ===")
        logger.info(f"Returning payload with {len(response_payload.get('MetricDataResults', []))} results")
        return response_payload
        
    except Exception as e:
        logger.error(f"Exception while processing timestamps: {str(e)}", exc_info=True)  # nosemgrep: logging-error-without-handling
        raise