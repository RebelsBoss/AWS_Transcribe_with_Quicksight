# AWS Transcribe with QuickSight
### 1. Setting up S3 buckets


Create three S3 buckets:
# bash
# Input bucket for audio files
aws s3 mb s3://"your-bucket-name"


# Bucket for transcription output
aws s3 mb s3://"your-bucket-name"


# Bucket of processed data for QuickSight
aws s3 mb s3://"your-bucket-name"
```


### 2. Set up an SQS queue


Create an SQS queue to process audio tasks:
```bash
aws sqs create-queue-- queue-name audio-processing-queue
```


### 3. Lambda functions


Expand two Lambda functions:


#### Lambda for transcribe
This function is triggered by SQS messages and initiates the Transcribe task.


#### Lambda for summarization
This function processes the transcription results and generates a summary.


### 4. S3 event notifications


Configure event notifications:
- Configure the input batch to send notifications to SQS when files are uploaded
- Configure the transcription output batch to run the Lambda summarization function


### 5. Set up QuickSight


- Create a QuickSight account if you don't have one
- Create a new dataset pointing to the processed data bucket
- Develop dashboards and visualizations to analyze transcription data


## Usage


1. Upload audio files to the input batch:
```bash
aws s3 cp "your-audio-file.mp3" s3://"your-bucket-name"/
```


2. The system automatically processes the file through the entire conveyor


3. Access QuickSight to view visualizations and analytics of the processed data


## Customization


The solution can be customized in several ways:
- Change the summary generation logic in the Lambda function
- Customize QuickSight visualizations to meet your needs
- Add additional processing or analytics steps


## Troubleshooting


Common problems and solutions:
- Check CloudWatch logs for Lambda function errors
- Check IAM permissions for all components
- Make sure S3 bucket notifications are configured correctly
- Check the SQS queue for unprocessed messages
