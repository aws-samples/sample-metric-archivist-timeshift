#!/bin/zsh
aws lambda invoke --function-name sam-TimeshiftLambda-1eWG0Ss7miVE --payload file://timeshift-invoke.json --cli-binary-format raw-in-base64-out l.out
