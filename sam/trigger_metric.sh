#!/bin/zsh

# Get the API URL from SAM outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name sam \
  --query 'Stacks[0].Outputs[?OutputKey==`MetricMigrationTriggerApi`].OutputValue' \
  --output text)

# Example metric data
read -r -d '' PAYLOAD <<EOF
{
  "namespace": "AWS/Lambda",
  "metricName": "Invocations",
  "destinationMetricName": "MigrationInvocations",
  "dimensions": [
    {
      "Name": "FunctionName",
      "Value": "sam-MigrateMetricFunction-9TbhGLeM4rUl"
    }
  ],
  "startTime": "2024-12-17T00:00:00Z",
  "endTime": "2024-12-18T00:00:00Z",
  "destinationKey": "test-key-01",
  "cloudwatchStats": ["Sum", "SampleCount"]
}
EOF

# Make the API call
curl -X POST "${API_URL}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" \
  | jq '.'
