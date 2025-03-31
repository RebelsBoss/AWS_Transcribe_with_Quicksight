import json
import logging
import boto3
import os
import csv
import re 

AWS_REGION = "your-region"
cleaned_output_bucket = "transcribe-output-123456789-987654321"
analysis_output_bucket = "finished-result-of-audio-123456789-987654321"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client(
    service_name='bedrock', 
    region_name=AWS_REGION
)
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime', 
    region_name=AWS_REGION
)

def clean_audio_segments(input_path, output_path):
    try:
        with open(input_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as e:
        logger.error(f"[ERROR] File could not be opened {input_path}: {e}")
        return None

    if "audio_segments" not in data:
        for key in data:
            if isinstance(data[key], dict) and "audio_segments" in data[key]:
                data = data[key]
                break

    if "audio_segments" not in data:
        logger.error("[ERROR] File does not contain a key 'audio_segments'")
        return None

    cleaned_data = []
    for seg in data["audio_segments"]:
        transcript = seg.get("transcript", "").strip()
        speaker = seg.get("speaker_label", "")
        if transcript and speaker:
            cleaned_data.append(f'"{transcript}"{speaker}')

    if not cleaned_data:
        logger.error("[ERROR] The cleaned file is empty or incorrectly formed")
        return None

    try:
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(cleaned_data, file, ensure_ascii=False, indent=2)
            logger.info(f"[OK] The cleaned data is saved in {output_path}")
    except Exception as e:
        logger.error(f"[ERROR] Could not save the cleared data to {output_path}: {e}")
        return None

    if not os.path.exists(output_path):
        logger.error(f"[ERROR] The file was not created at {output_path}")
        return None

    return cleaned_data

def analyze_text_with_bedrock(input_file, output_file):
    """
    Calls the Bedrock model and receives a JSON response.
    Saves the “raw” result in the 'output_file' (JSON) and returns it as a bucket (analysis_result).
    """
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            text_data = json.load(f)
    except Exception as e:
        logger.error(f"[ERROR] Unable to read cleared data from {input_file}: {e}")
        return None

    prompt_text = f"""
    You are a text analysis expert. Your task is to process and analyze the transcript of a conversation in Ukrainian.
    Give the answer in Ukrainian.
    Instructions:

    1. Identify and rename the speakers to “Manager” and “Customer” based on their roles.
    2. Rewrite the dialogue exactly as in the input, preserving the original text and flow. Each utterance should start on a new line with the corresponding speaker.
    3. Analyze the manager's conversation and identify the following parameters (select one of the given options):

    - Tone: [Calm, Interested, Formal, Informal, Humorous, Enthusiastic, Defiant, Irritated]
    - Solution: [Decided, not decided]
    - Greeted: [Yes, No]
    - Type of call: [Complaint, Consultation]

    Output Format (return JSON exactly in the following structure):

    "Tone": "<one of the options>",
    "Solution": "<one of the options>",
    "Greeted": "<one of the options>",
    "Type of call": "<one of the options>"

    Source Data:
    {text_data}
    """

    model_id = "amazon.titan-text-premier-v1:0"

    body_data = json.dumps({
        "inputText": prompt_text,
        "textGenerationConfig": {
            "maxTokenCount": 3072,
            "temperature": 0.2
        }
    })

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
            body=body_data
        )
        response_body = response["body"].read()
        response_json = json.loads(response_body)
        logger.info("[OK] Received a response from Bedrock")
    except Exception as e:
        logger.error(f"[ERROR] Error when calling Bedrock: {e}")
        return {"error": str(e)}

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(response_json, f, ensure_ascii=False, indent=2)
        logger.info(f"[OK] The results of the analysis are saved in {output_file}")
    except Exception as e:
        logger.error(f"[ERROR] The analysis results could not be saved in the {output_file}: {e}")
        return None

    return response_json

def extract_metrics_nested(analysis_data):
    """
    Reliably extracts metrics from Amazon Bedrock response.
    If the result is empty, it will try to re-extract JSON from outputText.
    """
    results = analysis_data.get("results", [])
    if not results:
        logger.warning("[WARNING] No results in response Bedrock.")
        return None

    first_result = results[0]
    raw_text = first_result.get("outputText", "")
    if not raw_text:
        logger.warning("[WARNING] Empty outputText in the response.")
        return None

    json_pattern = r"\{[\s\S]*?\}"
    match = re.search(json_pattern, raw_text)
    if not match:
        logger.error("[ERROR] JSON fragment not found in outputText")
        return None

    try:
        nested_data = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Unable to parse JSON after regex: {e}")
        return None

    metrics = {
        "Tone": nested_data.get("Tone", ""),
        "Solution": nested_data.get("Solution", ""),
        "Greeted": nested_data.get("Greeted", ""),
        "Type of call": nested_data.get("Type of call", "")
    }

    if all(value == "" for value in metrics.values()):
        logger.warning("[WARNING] Metrics are empty, let's try searching for JSON in full text again.")

        matches = re.findall(json_pattern, raw_text)
        for alternative_json in matches[1:]: 
            try:
                alternative_data = json.loads(alternative_json)
                if all(alternative_data.get(field) for field in ["Tone", "Solution", "Greeted", "Type of call"]):
                    logger.info("[OK] Alternative JSON fragment found.")
                    return {
                        "Tone": alternative_data.get("Tone", ""),
                        "Solution": alternative_data.get("Solution", ""),
                        "Greeted": alternative_data.get("Greeted", ""),
                        "Type of call": alternative_data.get("Type of call", "")
                    }
            except json.JSONDecodeError:
                continue

    return metrics

def write_metrics_to_csv(metrics_dict, input_json_path):
    """
    Writes (Tone, Solution, Greeted, Type of call) to a CSV with a header.
    The name of the CSV file is generated based on the name of the input JSON file.
    """
    def is_empty_metrics(metrics):
        return all(not value.strip() for value in metrics.values())

    base_name = os.path.splitext(input_json_path)[0] 
    base_name = os.path.splitext(base_name)[0] 
    
    csv_path = f"{base_name}.csv"

    if is_empty_metrics(metrics_dict):
        logger.warning("[WARNING] Empty metrics detected, re-analysis...")

        analysis_result = analyze_text_with_bedrock(input_json_path, input_json_path)
        if analysis_result:
            metrics_dict = extract_metrics_nested(analysis_result)
            if not metrics_dict or is_empty_metrics(metrics_dict):
                logger.error("[ERROR] Repeated analysis also yielded an empty result.")
            else:
                logger.info("[OK] The reanalysis is successful.")
        else:
            logger.error("[ERROR] The reanalysis failed.")
    
    if is_empty_metrics(metrics_dict):
        metrics_dict = {
            "Tone": "",
            "Solution": "",
            "Greeted": "",
            "Type of call": ""
        }

    base_name = os.path.splitext(input_json_path)[0]
    if base_name.endswith('.json'):
        base_name = os.path.splitext(base_name)[0] 
    csv_path = f"{base_name}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["Tone", "Solution", "Greeted", "Type of call"],
            delimiter=',',
            quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        writer.writerow(metrics_dict)

    return csv_path

def lambda_handler(event, context):
    s3 = boto3.client("s3")

    try:
        record = event["Records"][0]
        source_bucket = record["s3"]["bucket"]["name"]
        object_key = record["s3"]["object"]["key"]
    except KeyError as e:
        logger.error(f"[ERROR] Error reading event data: {e}")
        return {"statusCode": 400, "body": "Incorrect event structure"}

    local_input_file = f"/tmp/{os.path.basename(object_key)}"
    try:
        s3.download_file(source_bucket, object_key, local_input_file)
        logger.info(f"[OK] File {object_key} is loaded from the bucket {source_bucket}")
    except Exception as e:
        logger.error(f"[ERROR] Couldn't load file {object_key} from the bucket {source_bucket}: {e}")
        return {"statusCode": 500, "body": "File upload error"}

    local_cleaned_file = f"/tmp/cleaned_{os.path.basename(object_key)}"
    cleaned_data = clean_audio_segments(local_input_file, local_cleaned_file)
    if cleaned_data is None:
        logger.error("[ERROR] Error while processing a file")
        return {"statusCode": 500, "body": "Error while processing a file"}

    if not os.path.exists(local_cleaned_file):
        logger.error(f"[ERROR] File to download not found: {local_cleaned_file}")
        return {"statusCode": 500, "body": "File to download not found"}

    cleaned_object_key = f"cleaned/cleaned_{os.path.basename(object_key)}"
    try:
        s3.upload_file(local_cleaned_file, cleaned_output_bucket, cleaned_object_key)
        logger.info(f"[OK] The cleaned file is uploaded to the {cleaned_output_bucket} bucket under the key: {cleaned_object_key}")
    except Exception as e:
        logger.error(f"[ERROR] Could not upload the cleaned file to the bucket {cleaned_output_bucket}: {e}")
        return {"statusCode": 500, "body": "Error uploading a cleaned file"}

    local_cleaned_file_for_analysis = f"/tmp/for_analysis_{os.path.basename(object_key)}"
    try:
        s3.download_file(cleaned_output_bucket, cleaned_object_key, local_cleaned_file_for_analysis)
        logger.info(f"[OK] The cleaned file is reloaded from the bucket {cleaned_output_bucket}")
    except Exception as e:
        logger.error(f"[ERROR] Could not reload a cleaned file from the bucket {cleaned_output_bucket}: {e}")
        return {"statusCode": 500, "body": "Error re-uploading a cleaned file"}

    local_analysis_json = f"/tmp/analysis_{os.path.basename(object_key)}"
    analysis_result = analyze_text_with_bedrock(local_cleaned_file_for_analysis, local_analysis_json)
    if analysis_result is None:
        logger.error("[ERROR] Error during text analysis")
        return {"statusCode": 500, "body": "Text analysis error"}

    metrics = extract_metrics_nested(analysis_result)

    base_name = os.path.splitext(object_key)[0] 
    base_name = os.path.splitext(base_name)[0] 
    local_csv_file = f"/tmp/metrics_{os.path.basename(base_name)}.csv"
    try:
        write_metrics_to_csv(metrics, local_csv_file)
        logger.info("[OK] CSV with metrics generated")
    except Exception as e:
        logger.error(f"[ERROR] Error when generating CSV: {e}")
        return {"statusCode": 500, "body": "CSV creation error"}

    csv_object_key = f"analysis_csv/metrics_{os.path.basename(base_name)}.csv"
    try:
        s3.upload_file(local_csv_file, analysis_output_bucket, csv_object_key)
        logger.info(f"[OK] The CSV with metrics is loaded into the {analysis_output_bucket} bucket under the key: {csv_object_key}")
    except Exception as e:
        logger.error(f"[ERROR] CSV could not be loaded into the bucket {analysis_output_bucket}: {e}")
        return {"statusCode": 500, "body": "Error uploading CSV with metrics"}

    return {
        "statusCode": 200,
        "body": (
            f"The file has been processed."
            f"The cleaned data is saved in s3://{cleaned_output_bucket}/{cleaned_object_key}. "
            f"CSV with metrics saved in s3://{analysis_output_bucket}/{csv_object_key}"
        )
    }
