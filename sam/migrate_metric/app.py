import logging
import boto3
import json

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

metrics = boto3.client('cloudwatch')

def lambda_handler(event, context):
    """
    Simple echo function that logs and returns its input event
    """
    logger.info(f"Received event: {event}")
    event = event[0]

    # Check to make sure there is a body in the event
    if 'body' not in event:
        logger.error("No body found in event")
        return {
            'statusCode': 400,
            'message': 'No body found in event'
        }
    
    body = event['body']
    
    # Parse body into json
    body = json.loads(body)

    # Check to see if the event does not include a metricName
    if 'metricName' not in body or body['metricName'] == '':
        logger.error("No metricName found in body")
        return {
            'statusCode': 400,
            'message': 'No metricName found in body'
        }
    
    metricName = body['metricName']

    # Check to see if the event does not include a namespace
    if 'namespace' not in body or body['namespace'] == '':
        logger.error("No namespace found in body")
        return {
            'statusCode': 400,
            'message': 'No namespace found in body'
        }
    
    namespace = body['namespace']

    metricsListFromCloudWatch = metrics.list_metrics(
        Namespace=namespace,
        MetricName=metricName
    )

    logger.info(f"Metrics found: {metricsListFromCloudWatch}")

    return {
        'statusCode': 200,
        'input': event,
        'message': 'Event echoed successfully'
    }
