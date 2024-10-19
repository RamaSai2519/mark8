import os
import re
import pytz
import json
import boto3
import requests
import subprocess
from datetime import datetime
from urllib.parse import urlparse, ParseResult
from config import DEEPGRAM_API_KEY, AWS_ACCESS_KEY, AWS_SECRET_KEY, GAMES_PROCESSOR_URL, errorlog_collection

s3_client = boto3.client(
    's3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)


def log(callId: str, message: str) -> None:
    datetime_now = datetime.now(pytz.utc)
    current_time = datetime_now.strftime("%Y-%m-%d %H:%M:%S")
    error_log: dict = errorlog_collection.find_one({"callId": callId})
    if error_log:
        logs: list = error_log.get("logs", [])
        logs.append({"message": message, "time": datetime_now})
        errorlog_collection.update_one(
            {"callId": callId}, {"$set": {"logs": logs}})
    else:
        errorlog_collection.insert_one(
            {"callId": callId, "logs": [{"message": message, "time": datetime_now}]})
    print(current_time, message)


class Helper:
    def __init__(self, callId: str, audio_filename: str, recording_url: str, user_calls_count: int) -> None:
        self.callId = callId
        self.recording_url = recording_url
        self.audio_filename = audio_filename
        self.user_calls_count = user_calls_count

    def extract_json(self, format_spec: str) -> dict:
        def clean_json(json_str: str) -> str:
            return json_str.replace("\n", "").replace("'", "\"").replace(" ", "").replace("```", "").replace("json", "").strip()

        try:
            if "json" in format_spec:
                match = re.search(r'```json\n(.*?)```', format_spec, re.DOTALL)
                if match:
                    response_text = clean_json(match.group(1))
                    response_text = json.loads(response_text)
                    return response_text
            cleaned_format_spec = clean_json(format_spec)
            cleaned_format_spec = json.loads(cleaned_format_spec)
            return cleaned_format_spec
        except Exception:
            log(self.callId, f"Error decoding JSON: {format_spec}")
            return {}

    @staticmethod
    def check_for_transcript_file(callId: str) -> bool:
        bucket_name = 'sukoontest'
        filename = f"{callId}.txt"
        try:
            s3_client.head_object(Bucket=bucket_name, Key=filename)
            return True
        except Exception as e:
            return False

    @staticmethod
    def upload_transcript(transcript: str, callId: str) -> str:
        bucket_name = 'sukoontest'
        filename = f"{callId}.txt"
        url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
        with open(filename, 'w') as file:
            file.write(transcript)
        with open(filename, 'rb') as data:
            s3_client.upload_fileobj(data, bucket_name, filename)

        os.remove(filename)

        return url

    @staticmethod
    def get_transcript(callId: str) -> str:
        bucket_name = 'sukoontest'
        filename = f"{callId}.txt"
        response = s3_client.get_object(Bucket=bucket_name, Key=filename)
        transcript = response['Body'].read().decode('utf-8')
        return transcript

    @staticmethod
    def get_transcript_url(callId: str) -> str:
        bucket_name = 'sukoontest'
        filename = f"{callId}.txt"
        url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
        return url

    @staticmethod
    def clean_dict(doc: dict, dataClass) -> dict:
        if doc:
            document_fields = set(dataClass.__annotations__.keys())
            doc = {k: v for k, v in doc.items() if k in document_fields}
        return doc

    @staticmethod
    def duration_str_to_seconds(duration: str) -> int:
        duration = duration.split(':')
        hours, minutes, seconds = map(int, duration)
        return hours * 3600 + minutes * 60 + seconds

    @staticmethod
    def get_file_path(filename: str) -> str:
        return os.path.join(os.getcwd(), filename)

    def download_audio(self) -> None:
        if not self.recording_url.startswith("http"):
            return None
        url: ParseResult = urlparse(self.recording_url)
        url = url.scheme + "://" + url.netloc + url.path
        params = {"callid": self.callId}
        response = requests.get(url, params=params)
        with open(self.audio_filename, "wb") as f:
            f.write(response.content)
        log(self.callId, "Audio downloaded")

    def download_and_transcribe_audio(self) -> bool:
        if Helper.check_for_transcript_file(self.callId):
            return Helper.get_transcript(self.callId)
        self.download_audio()

        curl_command = [
            'curl', '--request', 'POST',
            '--url', 'https://api.deepgram.com/v1/listen?model=whisper-large&diarize=true&punctuate=true&utterances=true',
            '--header', f'Authorization: Token {DEEPGRAM_API_KEY}',
            '--header', 'content-type: audio/mp3',
            '--data-binary', f'@{self.audio_filename}'
        ]

        log(self.callId, "Transcribing audio")
        result = subprocess.run(
            curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            log(self.callId, f"Error: {result.stderr}")
            return False

        jq_command = [
            'jq', '-r', '.results.utterances[] | "[Speaker:\(.speaker)] \(.transcript)"']
        jq_result = subprocess.run(jq_command, input=result.stdout,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if jq_result.returncode != 0:
            log(self.callId, f"Error: {jq_result.stderr}")
            return False

        log(self.callId, "Transcription completed")
        os.remove(self.audio_filename)
        Helper.upload_transcript(jq_result.stdout, self.callId)
        return jq_result.stdout

    def get_guidelines(self) -> str:
        if self.user_calls_count == 1:
            with open("texts/guidelines.txt", "r", encoding="utf-8") as file:
                guidelines = file.read()
        else:
            with open("texts/guidelines2.txt", "r", encoding="utf-8") as file:
                guidelines = file.read()
        return guidelines

    def extract_score(self, score_str: str) -> float | int:
        score_match = re.findall(r"\b(?:\d{2}|100)\b", score_str)
        try:
            conversation_score = int(score_match[0])
            return conversation_score / 20
        except Exception as e:
            log(self.callId, f"Error calculating total score: {str(e)}")
            return 0

    def run_step(self, step_name: str, step_function: callable) -> bool:
        log(self.callId, f"started: {step_name}")
        result = step_function()
        if not result:
            log(self.callId, result)
            log(self.callId, f"failed: {step_name}")
            return False

        log(self.callId, f"completed: {step_name}")
        return True

    @staticmethod
    def updater(callId: str, expert_id: str, expert_number: str) -> None:
        payload = json.dumps({
            "expert_id": expert_id,
            "expert_number": expert_number
        })
        headers = {'Content-Type': 'application/json'}
        url = GAMES_PROCESSOR_URL + '/actions/expert_scores'
        response = requests.request("POST", url, headers=headers, data=payload)
        log(callId, f"Lambda response: {response.text}")
        return response.text
