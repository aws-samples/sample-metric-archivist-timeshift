from __future__ import print_function
import urllib3
import json
import re
import boto3
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3tables = boto3.client('s3tables')
athena = boto3.client('athena')
glue = boto3.client('glue')

### Begin cfnresponse snip.
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    responseBody = {
        'Status' : responseStatus,
        'Reason' : reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId' : physicalResourceId or context.log_stream_name,
        'StackId' : event['StackId'],
        'RequestId' : event['RequestId'],
        'LogicalResourceId' : event['LogicalResourceId'],
        'NoEcho' : noEcho,
        'Data' : responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:")
    print(json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        print("Status code:", response.status)


    except Exception as e:
        print("send(..) failed executing http.request(..):", mask_credentials_and_signature(e))
 
 
def mask_credentials_and_signature(message):
    message = re.sub(r'X-Amz-Credential=[^&\s]+', 'X-Amz-Credential=*****', message, flags=re.IGNORECASE)
    return re.sub(r'X-Amz-Signature=[^&\s]+', 'X-Amz-Signature=*****', message, flags=re.IGNORECASE)

### END cfnresponse snip

def lambda_handler(event, context):
    """
    Lambda function that handles namespace setup as a CloudFormation Custom Resource
    """
    try:
        logger.info('Received event: %s', event)
        response_data = {}
        
        namespace_name = event['ResourceProperties'].get("Namespace")
        tableBucketArn = event['ResourceProperties'].get('TableBucketArn')
        table_name = event['ResourceProperties'].get('TableName')
        accountNumber = event['ResourceProperties'].get('AccountNumber')
        tempS3Path = event['ResourceProperties'].get('TempS3Path')

        if event['RequestType'] in ['Create', 'Update']:
            try:
                # Create the namespace
                response = s3tables.create_namespace(
                    tableBucketARN=tableBucketArn,
                    namespace=[namespace_name]
                )
                
                if response['tableBucketArn'] == tableBucketArn and response['namespace'][0] == namespace_name:
                    logger.info(f"Created namespace: {namespace_name}")
                    response_data['namespace'] = namespace_name
                    response_data['tableBucketArn'] = tableBucketArn
                    response_data['change-type'] = "CREATED"
                    logger.info(f"Successfully created namespace: {namespace_name}")
            except s3tables.exceptions.ConflictException as e:
                # If the namespace already exists, consider it created
                logger.info(f"Namespace {namespace_name} already exists, considering it created")
                response_data['namespace'] = namespace_name
                response_data['tableBucketArn'] = tableBucketArn
                response_data['bucket-change-type'] = "EXISTS"
            except Exception as e:
                logger.error(f"Error creating/updating namespace: {str(e)}")
                raise
            
            try:
                tableCreateResponse = s3tables.create_table(
                    tableBucketARN=tableBucketArn,
                    namespace=namespace_name,
                    name=table_name,
                    format="ICEBERG"
                )
                response_data['table'] = table_name
                response_data['table-change-type'] = "EXISTS"
            except s3tables.exceptions.ConflictException as e:
                # If the table already exists, consider it created
                logger.info(f"Table {table_name} already exists, considering it created")
                response_data['table'] = table_name
                response_data['table-change-type'] = "EXISTS"

            try:
                metadataResponse = s3tables.get_table_metadata_location(
                    tableBucketARN=tableBucketArn,
                    namespace=namespace_name,
                    name=table_name
                )  

                versionToken = metadataResponse['versionToken']
                warehouseLocation = metadataResponse['warehouseLocation']

                print(warehouseLocation)

                athenaResponse = athena.start_query_execution(
                    QueryString=f"CREATE TABLE default.temp_table (region string, namespace string, metricName string, dimensionName string, dimensionValue string) partitioned by (region) LOCATION '{warehouseLocation}' TBLPROPERTIES ( 'table_type' = 'ICEBERG' )",
                    ResultConfiguration={
                        'OutputLocation': warehouseLocation
                    }
                )

                athenaQueryExecutionId = athenaResponse['QueryExecutionId']
            except Exception as e:
                logger.error(f"Error creating table: {str(e)}")
                raise

            while True:
                athenaQueryResponse = athena.get_query_execution(QueryExecutionId=athenaQueryExecutionId)
                queryStatus = athenaQueryResponse['QueryExecution']['Status']['State']
                if queryStatus in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                else:
                    logger.info(f"Athena Query status: {queryStatus}")
                    time.sleep(5)
            
            athenaResults = athena.get_query_results(
                QueryExecutionId=athenaQueryExecutionId
            )

            print(athenaResults)



        elif event['RequestType'] == 'Delete':
            try:
                # Delete the namespace
                try:
                    s3tables.delete_namespace(
                        tableBucketARN=tableBucketArn,
                        namespace=[namespace_name]
                    )
                    logger.info(f"Deleted namespace: {namespace_name}")
                except Exception as e:
                    # If the namespace doesn't exist, consider it deleted
                    logger.info(f"Namespace {namespace_name} not found, considering it deleted")
            except Exception as e:
                logger.error(f"Error deleting namespace: {str(e)}")
                raise
                
        send(event, context, SUCCESS, response_data)
        
    except Exception as e:
        logger.error('Error: %s', str(e))
        send(event, context, FAILED, {})