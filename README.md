# Metric Archivist

A serverless AWS application that migrates CloudWatch metrics to S3 for long-term archival and cost optimization, with support for time-shifted data visualization through a custom CloudWatch connector.

## Overview

CloudWatch metric storage can be expensive for long-term retention. This system archives older metrics to cheaper S3 storage while maintaining access to historical data through a custom CloudWatch data source connector that supports time-shifting capabilities.

## Architecture

- **MetricMigrationTrigger**: Lambda function that accepts migration requests via API Gateway POST `/migrate`
- **MigrateMetricFunction**: Lambda function that processes SQS messages to migrate metrics from CloudWatch to S3
- **SQS Queue**: Decouples trigger from migration work with dead letter queue for failed attempts
- **S3 Bucket**: Stores archived metrics with encryption and versioning
- **Custom CloudWatch Connector**: Enables time-shifted visualization of archived metrics

## Features

### Metric Migration
- Migrates CloudWatch metrics to S3 for cost-effective long-term storage
- Supports all CloudWatch statistics (Average, Min, Max, Sum, SampleCount, IQM, p99, tm99, tc99, ts99)
- Validates request parameters (namespace, metric name, dimensions, time ranges)
- Asynchronous processing with error handling and retry mechanisms
- VPC-secured Lambda execution

### Time-Shifted Data Visualization
The custom CloudWatch connector allows you to:
- Graph archived metric series against current CloudWatch metrics
- Apply arbitrary time shifts to reference data
- Create year-over-year comparisons (e.g., current day vs. same day previous year)
- Build dashboards comparing historical patterns with current performance

**Example Use Case**: An eCommerce operator can create a dashboard showing current day Order Rate vs. the same day from the previous year, enabling easy year-over-year performance comparison.

## API Usage

### Trigger Metric Migration

```bash
POST /migrate
```

**Request Body:**
```json
{
  "namespace": "AWS/EC2",
  "metricName": "CPUUtilization",
  "dimensions": [
    {"Name": "InstanceId", "Value": "i-1234567890abcdef0"}
  ],
  "startTime": "2024-01-01T00:00:00Z",
  "endTime": "2024-01-31T23:59:59Z",
  "destinationMetricName": "ArchivedCPUUtilization",
  "destinationKey": "ec2/cpu-utilization/2024-01",
  "cloudwatchStats": ["Average", "Maximum"]
}
```

## Custom CloudWatch Connector

The application includes a custom CloudWatch data source connector that enables time-shifted visualization of archived metrics. This connector implements the [CloudWatch Custom Data Source API](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_MultiDataSources-Connect-Custom.html).

### Configuration
- **Data Source Name**: Configurable via `DataSourceName` parameter
- **Code Location**: Specified via `DataSourceCodeBucket` and `DataSourceCodeKey` parameters
- **Runtime**: Node.js 18.x

### Time-Shifting Capabilities
- Apply arbitrary time offsets to archived metric series
- Compare current metrics with historical data from any time period
- Enable year-over-year, month-over-month, or custom period comparisons

## Deployment

```bash
# Build and deploy
sam build --use-container
sam deploy --guided

# Required parameters:
# - DataSourceCodeBucket: S3 bucket containing connector code
# - DataSourceCodeKey: S3 key of connector code
# - DataSourceName: Name for the custom data source
```

## Testing

The `k6/` directory contains load testing scripts for generating test data and validating the migration pipeline under various load conditions.

```bash
k6 run k6/script.js
```

## Cost Optimization

- CloudWatch metrics: ~$0.30 per metric per month for detailed monitoring
- S3 Standard storage: ~$0.023 per GB per month
- Significant cost savings for long-term metric retention (>90 days)

## Security

- S3 bucket encryption with AES-256
- VPC-secured Lambda execution
- Public access blocked on S3 bucket
- IAM roles with least-privilege access
