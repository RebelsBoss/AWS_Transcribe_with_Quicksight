import json
import boto3
import urllib.parse
from datetime import datetime

s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe')

OUTPUT_BUCKET = 'your-output-bucket'

def lambda_handler(event, context):
    try:
        if 'Records' not in event or not event['Records']:
            raise ValueError("No records found in event.")

        for sqs_record in event['Records']:
            message_body = json.loads(sqs_record['body'])

            if 'Records' not in message_body or not message_body['Records']:
                raise ValueError("No S3 records found in message.")

            for s3_record in message_body['Records']:
                bucket_name = s3_record.get('s3', {}).get('bucket', {}).get('name')
                object_key = s3_record.get('s3', {}).get('object', {}).get('key')

                if not bucket_name or not object_key:
                    raise ValueError("Bucket name or object key missing in S3 record.")

                object_key = urllib.parse.unquote_plus(object_key)

                job_name = f"transcribe-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

                file_uri = f"s3://{bucket_name}/{object_key}"

                response = transcribe_client.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={'MediaFileUri': file_uri},
                    MediaFormat=object_key.split('.')[-1],
                    Settings={
                        'ShowSpeakerLabels': True,
                        'MaxSpeakerLabels': 2,
                        'ChannelIdentification': True
                    },
                    LanguageCode='uk-UA',
                    OutputBucketName=OUTPUT_BUCKET
                )

                print(f"Transcription job {job_name} started successfully for file {object_key}.")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Transcription jobs started successfully.'})
        }

    except Exception as e:
        print(f"Error processing event: {json.dumps(event)} - {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
