#!/bin/bash

# Script to introspect AWS account for API Gateway URL and run k6 load test
# Usage: ./run-k6-test.sh [stack-name] [region]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DEFAULT_STACK_NAME="metric-timeshift"
DEFAULT_REGION="us-east-1"

# Get stack name from argument or use default
STACK_NAME="${1:-$DEFAULT_STACK_NAME}"
REGION="${2:-$DEFAULT_REGION}"

echo -e "${GREEN}=== K6 Load Test Runner ===${NC}"
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo -e "${RED}Error: k6 is not installed${NC}"
    echo "Please install k6: https://k6.io/docs/getting-started/installation/"
    exit 1
fi

# Check if stack exists
echo -e "${YELLOW}Checking if stack exists...${NC}"
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
    echo -e "${RED}Error: Stack '$STACK_NAME' not found in region '$REGION'${NC}"
    echo ""
    echo "Available stacks:"
    aws cloudformation list-stacks --region "$REGION" \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
        --query 'StackSummaries[].StackName' \
        --output table
    exit 1
fi

# Get the API URL from CloudFormation outputs
echo -e "${YELLOW}Retrieving API Gateway URL from CloudFormation...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`HelloWorldApi`].OutputValue' \
    --output text)

if [ -z "$API_URL" ] || [ "$API_URL" == "None" ]; then
    echo -e "${RED}Error: Could not find HelloWorldApi output in stack${NC}"
    echo ""
    echo "Available outputs:"
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' \
        --output table
    exit 1
fi

echo -e "${GREEN}✓ Found API URL: $API_URL${NC}"
echo ""

# Verify the API is accessible
echo -e "${YELLOW}Testing API endpoint...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL" || echo "000")

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✓ API is accessible (HTTP $HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" == "000" ]; then
    echo -e "${RED}⚠ Warning: Could not reach API endpoint${NC}"
    echo "This might be a network issue. Continuing anyway..."
else
    echo -e "${YELLOW}⚠ Warning: API returned HTTP $HTTP_CODE${NC}"
    echo "Continuing anyway..."
fi
echo ""

# Run k6 test
echo -e "${GREEN}=== Starting K6 Load Test ===${NC}"
echo "Command: k6 run -e API_URL=$API_URL k6/script.js"
echo ""

k6 run -e API_URL="$API_URL" k6/script.js

echo ""
echo -e "${GREEN}=== Test Complete ===${NC}"
