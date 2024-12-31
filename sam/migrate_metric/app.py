import logging
import boto3
import json
import datetime
import os

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

metrics = boto3.client('cloudwatch')
s3_client = boto3.client('s3')

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

        if 'destinationMetricName' not in body or body['destinationMetricName'] == '':
            logger.error("No destination metric name found in body")
            return {
                'statusCode': 400, 
                'message': 'No destination metric name found in body'
            }

        destinationMetricName = body['destinationMetricName']

        if 'destinationKey' not in body or body['destinationKey'] == '':
            logger.error("No destination key found in body")
            return {
                'statusCode': 400,
                'message': 'No destination key found in body'
            }
        
        destinationKey = body['destinationKey']

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

    destinationMetrics = []
    fileHeader = "timestamp,"
    for queryResult in dataToSync:
        sourceStatName = queryResult['query']['MetricStat']['Stat']
        headerEntry = destinationMetricName+'-'+sourceStatName
        destinationMetrics.append(headerEntry)
        fileHeader = fileHeader+headerEntry+","
    
    fileHeader = fileHeader[:-1]

    timestampKeyedMetrics = {}
    with open('/tmp/to_upload', 'w') as tempFile:
        tempFile.write(fileHeader + '\n')
        for queryResult in dataToSync:
            sourceStatName = queryResult['query']['MetricStat']['Stat']
            headerEntry = destinationMetricName+'-'+sourceStatName
            zipped = zip(queryResult['results']['Timestamps'], queryResult['results']['Values'])
            for z in zipped:
                if z[0] not in timestampKeyedMetrics:
                    timestampKeyedMetrics[z[0]] = {}
                timestampKeyedMetric = timestampKeyedMetrics[z[0]]
                timestampKeyedMetric[headerEntry] = z[1]
        for timestamp, values in timestampKeyedMetrics.items():
            s = timestamp.isoformat()+","
            for headerEntry in destinationMetrics:
                s = s + str(values[headerEntry]) + ","
            s = s[:-1]
            tempFile.write(s+'\n')

    try:
        s3_key = destinationKey
        s3_client.upload_file(
            '/tmp/to_upload',
            os.environ['ARCHIVED_METRICS_BUCKET_NAME'],
            s3_key
        )
        logger.info(f"Successfully uploaded metrics to s3://{os.environ['ARCHIVED_METRICS_BUCKET_NAME']}/{s3_key}")

    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise

    print("DESTINATION METRICS")
    print(json.dumps(destinationMetrics))

    print("BATCH FAILURES")
    print(json.dumps(batchFailures, default=str))
    return batchFailures