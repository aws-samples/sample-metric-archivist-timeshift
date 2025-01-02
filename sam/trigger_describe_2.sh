#!/bin/zsh
aws lambda invoke --function-name s3-csv-cloudwatch-reader --payload file://timeshift-invoke.json --cli-binary-format raw-in-base64-out l.out
