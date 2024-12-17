import logging
import boto3
import json
import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

metrics = boto3.client('cloudwatch')

CLOUDWATCH_STATISTICS = ["Average", "Minimum", "Maximum", "Sum", "SampleCount", "IQM", "p99", "tm99", "tc99", "ts99"]

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    count = 0
    batchFailures = {
        'batchItemFailures': []
    }

    for record in event['Records']:
        body = record['body']
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

        if 'startTime' not in body or body['startTime'] == '':
            logger.error("No startTime found in body")
            raise RuntimeError("No startTime found in body")
        if 'endTime' not in body or body['endTime'] == '':
            logger.error("No endTime found in body")
            raise RuntimeError("No endTime found in body")
        
        windowStartTimeStr = body['startTime']
        windowEndTimeStr = body['endTime']

        try:
            windowStartTime = datetime.datetime.fromisoformat(windowStartTimeStr.replace('Z', '+00:00'))
        except Exception as e:
            logger.error("Error parsing startTime")
            raise RuntimeError("Error parsing startTime")

        try:
            windowEndTime = datetime.datetime.fromisoformat(windowEndTimeStr.replace('Z', '+00:00'))
        except Exception as e:
            logger.error("Error parsing endTime")
            raise RuntimeError("Error parsing endTime")

        if 'dimensions' not in body:
            logger.info("No dimensions found in body - this might be fine (but probably not.)")
            dimensions = []
        else:
            dimensions = body['dimensions']

        continuePaginating = True
        nextToken = None;
        seriesToSync = []
        while continuePaginating:
            if nextToken is not None:
                print(f"Paginating from a next token")
            else:
                print("Starting Metric Query")

            if nextToken is None:
                metricsListFromCloudWatch = metrics.list_metrics(
                    Namespace=namespace,
                    MetricName=metricName,
                    Dimensions=dimensions
                )
            else:
                metricsListFromCloudWatch = metrics.list_metrics(
                    Namespace=namespace,
                    MetricName=metricName,
                    Dimensions=dimensions,
                    NextToken=nextToken
                )
            if 'NextToken' in metricsListFromCloudWatch:
                nextToken = metricsListFromCloudWatch['NextToken']
                logger.info(f"Found nextToken: {nextToken}")
                continuePaginating = True
            else:
                logger.info("No nextToken found")
                continuePaginating = False

            seriesToSync.append(metricsListFromCloudWatch['Metrics'])

        logger.info(f"Metrics to sync: {metricsListFromCloudWatch}")

        dataToSync = []
        for metric in metricsListFromCloudWatch['Metrics']:
            logger.info(f"Syncing metric: {metric}")
            for stat in CLOUDWATCH_STATISTICS:
                # Check to see if the metric has dimensions
                namespace = metric['Namespace']
                name = metric['MetricName']
                dimensions = metric['Dimensions']
                print(f"Ready to fetch {stat}")
                # Fetch the metric data from CloudWatch
                count += 1
                continueFetchingData = True
                nextDataToken = None
                while continueFetchingData:
                    if nextDataToken == None:
                        fetchedMetricData = metrics.get_metric_data(
                            MetricDataQueries=[
                                {
                                    'Id': "r"+str(count),
                                    'MetricStat': {
                                        'Metric': {
                                            'Namespace': namespace,
                                            'MetricName': name,
                                            'Dimensions': dimensions
                                        },
                                        'Period': 60,
                                        'Stat': stat
                                    }
                                }
                            ],
                            StartTime=windowStartTime,
                            EndTime=windowEndTime
                        )
                    else:
                            fetchedMetricData = metrics.get_metric_data(
                            MetricDataQueries=[
                                {
                                    'Id': "r"+str(count),
                                    'MetricStat': {
                                        'Metric': {
                                            'Namespace': namespace,
                                            'MetricName': name,
                                            'Dimensions': dimensions
                                        },
                                        'Period': 60,
                                        'Stat': stat
                                    }
                                }
                            ],
                            StartTime=windowStartTime,
                            EndTime=windowEndTime,
                            NextToken=nextDataToken
                        )
                            
                    if 'NextToken' in fetchedMetricData:
                        logger.info(f"Found nextToken: {fetchedMetricData['NextToken']}")
                        continueFetchingData = True
                    else:
                        logger.info("No nextToken found")
                        continueFetchingData = False
                        nextDataToken = None
                    
                    dataToSync.append(
                        { 
                            'results': fetchedMetricData['MetricDataResults'][0],
                            'query': {
                                'MetricStat': {
                                    'Metric': {
                                        'Namespace': namespace,
                                        'MetricName': name,
                                        'Dimensions': dimensions
                                    },
                                    'ReturnData': True,
                                    'Period': 60,
                                    'Stat': stat
                                }
                            }
                        }
                    )
                    
            
    print("DATA TO SYNC")
    print(json.dumps(dataToSync, default=str))
    print("BATCH FAILURES")
    print(json.dumps(batchFailures, default=str))
    return batchFailures