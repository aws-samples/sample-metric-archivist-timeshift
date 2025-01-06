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
      "Value": "sam-HelloWorldFunction-pQR2ob6Ha7yL"
    }
  ],
  "startTime": "2025-01-03T21:54:00Z",
  "endTime": "2025-01-03T22:37:00Z",
  "destinationKey": "helloworld-reference-01",
  "cloudwatchStats": ["Sum", "Minimum", "Maximum", "Average", "SampleCount"]
}
EOF

# Make the API call
curl -X POST "${API_URL}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" \
  | jq '.'
