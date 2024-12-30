#!/bin/zsh

aws ssm start-session --region us-east-2 --target i-0670c5d48ed88b034 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host="sam-metricsdatabase-msv4hvq03u3m.cluster-crkamgu0m9qf.us-east-2.rds.amazonaws.com",portNumber="5432",localPortNumber="5432"
