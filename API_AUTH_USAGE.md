# API Authentication Usage Guide

## Getting Your API Key

After deploying the stack, retrieve your API key:

```bash
# Get the command from stack outputs
aws cloudformation describe-stacks --stack-name <your-stack-name> --query 'Stacks[0].Outputs[?OutputKey==`GetApiKeyCommand`].OutputValue' --output text

# Or run directly (replace <your-stack-name>)
API_KEY=$(aws cloudformation describe-stacks --stack-name <your-stack-name> --query 'Stacks[0].Outputs[?OutputKey==`ApiKeyId`].OutputValue' --output text | xargs -I {} aws apigateway get-api-key --api-key {} --include-value --query 'value' --output text)

echo $API_KEY
```

## Using with httpie

```bash
# Set your API key as an environment variable
export API_KEY="your-api-key-here"

# GET request to /hello
http GET https://your-api-id.execute-api.region.amazonaws.com/Prod/hello \
  x-api-key:$API_KEY

# POST request to /migrate
http POST https://your-api-id.execute-api.region.amazonaws.com/Prod/migrate \
  x-api-key:$API_KEY \
  namespace="AWS/Lambda" \
  metric_name="Invocations"
```

## Using with k6

Update your k6 script to include the API key header:

```javascript
import http from 'k6/http';
import { check } from 'k6';

// Set your API key here or pass via environment variable
const API_KEY = __ENV.API_KEY || 'your-api-key-here';

export const options = {
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 20 },
    { duration: '30s', target: 0 },
  ],
};

export default function () {
  const params = {
    headers: {
      'x-api-key': API_KEY,
      'Content-Type': 'application/json',
    },
  };

  // GET request
  const getRes = http.get(
    'https://your-api-id.execute-api.region.amazonaws.com/Prod/hello',
    params
  );
  
  check(getRes, {
    'GET status is 200': (r) => r.status === 200,
  });

  // POST request
  const postPayload = JSON.stringify({
    namespace: 'AWS/Lambda',
    metric_name: 'Invocations',
  });

  const postRes = http.post(
    'https://your-api-id.execute-api.region.amazonaws.com/Prod/migrate',
    postPayload,
    params
  );

  check(postRes, {
    'POST status is 200': (r) => r.status === 200,
  });
}
```

Run k6 with environment variable:

```bash
k6 run -e API_KEY=$API_KEY script.js
```

## Testing Without Authentication (Should Fail)

```bash
# This should return 403 Forbidden
http GET https://your-api-id.execute-api.region.amazonaws.com/Prod/hello

# Expected response:
# {"message":"Forbidden"}
```

## Rate Limits

The API is configured with:
- **Rate Limit**: 100 requests/second
- **Burst Limit**: 200 requests
- **Daily Quota**: 10,000 requests/day

Adjust these in the `template.yaml` under `Globals.Api.Auth.UsagePlan` if needed.
