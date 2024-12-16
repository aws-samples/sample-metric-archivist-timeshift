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
  "dimensions": [
    {
      "Name": "FunctionName",
      "Value": "MyTestFunction"
    }
  ],
  "startTime": "2024-01-01T00:00:00Z",
  "endTime": "2024-01-02T00:00:00Z"
}
EOF

echo ${API_URL}
echo ${PAYLOAD}

# Make the API call
curl -X POST "${API_URL}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" \
  | jq '.'
