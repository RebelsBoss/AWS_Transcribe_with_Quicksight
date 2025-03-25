# AWS Transcribe with QuickSight

## Project Overview
This repository contains the infrastructure and code for an automated audio processing pipeline that transcribes audio files, generates summaries, and visualizes the results using AWS QuickSight.

The solution leverages several AWS services to create a serverless architecture for processing audio files at scale:
- Amazon S3 for storage
- AWS Lambda for serverless computing
- Amazon Transcribe for speech-to-text conversion
- AWS SQS for message queuing
- Amazon QuickSight for data visualization and analytics

## Architecture

The system follows this workflow:

1. Audio files are uploaded to a designated S3 bucket
2. The upload event triggers an SQS message
3. An AWS Lambda function consumes the message and initiates an Amazon Transcribe job
4. Transcribe processes the audio and stores the result in an output S3 bucket
5. A second Lambda function is triggered when the transcription is complete
6. This function processes the transcription, creates a summary, and extracts key insights
7. The processed data is stored in a final S3 bucket
8. Amazon QuickSight connects to this bucket to visualize the data and provide analytics

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Knowledge of AWS services (S3, Lambda, SQS, Transcribe, QuickSight)

## Setup Instructions

### 1. S3 Buckets Setup

Create three S3 buckets:
```bash
# Input bucket for audio files
aws s3 mb s3://input-audio-bucket

# Transcription output bucket
aws s3 mb s3://transcription-output-bucket

# Processed data bucket for QuickSight
aws s3 mb s3://processed-data-bucket
```

### 2. SQS Queue Setup

Create an SQS queue to handle the audio processing jobs:
```bash
aws sqs create-queue --queue-name audio-processing-queue
```

### 3. Lambda Functions

Deploy two Lambda functions:

#### Transcription Lambda
This function is triggered by SQS messages and starts Transcribe jobs.

#### Summary Lambda
This function processes the transcription results and generates summaries.

### 4. S3 Event Notifications

Configure event notifications to trigger the workflow:
- Set up the input bucket to send notifications to SQS when files are uploaded
- Set up the transcription output bucket to trigger the summary Lambda function

### 5. QuickSight Setup

- Set up a QuickSight account if you don't have one
- Create a new dataset pointing to the processed data bucket
- Design dashboards and visualizations to analyze the transcription data

## Usage

1. Upload audio files to the input bucket:
```bash
aws s3 cp your-audio-file.mp3 s3://input-audio-bucket/
```

2. The system automatically processes the file through the entire pipeline

3. Access QuickSight to view visualizations and analytics of the processed data

## Customization

The solution can be customized in several ways:
- Modify the summary generation logic in the Lambda function
- Adjust the QuickSight visualizations based on your specific needs
- Add additional processing steps or analytics as required

## Troubleshooting

Common issues and solutions:
- Check CloudWatch Logs for Lambda function errors
- Verify IAM permissions for all components
- Ensure S3 bucket notifications are properly configured
- Check SQS queue for unprocessed messages
