import os
import re
import json
import boto3
import requests
import subprocess
from urllib.parse import urlparse, ParseResult
from config import DEEPGRAM_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, MAIN_LAMBDA_URL as url

s3_client = boto3.client(
    's3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


class Helper:
    def __init__(self, callId: str, audio_filename: str, recording_url: str, user_calls_count: int) -> None:
        self.callId = callId
        self.recording_url = recording_url
        self.audio_filename = audio_filename
        self.user_calls_count = user_calls_count

    @staticmethod
    def extract_json(format_spec: str) -> dict:
        if "json" in format_spec:
            response_text = re.search(
                r'```json\n(.*?)```', format_spec, re.DOTALL)
            if response_text:
                response_text = response_text.group(1)
                response_text = response_text.replace("\n", "")
                return json.loads(response_text)
        return json.loads(format_spec)

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

    def download_audio(self) -> None:
        if not self.recording_url.startswith("http"):
            return None
        url: ParseResult = urlparse(url)
        url = url.scheme + "://" + url.netloc + url.path
        params = {"callid": self.callId}
        response = requests.get(url, params=params)
        with open(self.audio_filename, "wb") as f:
            f.write(response.content)
        print(f"Downloaded audio for call ID: {self.callId}")

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

        result = subprocess.run(
            curl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False

        jq_command = [
            'jq', '-r', '.results.utterances[] | "[Speaker:\(.speaker)] \(.transcript)"']
        jq_result = subprocess.run(jq_command, input=result.stdout,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if jq_result.returncode != 0:
            print(f"Error: {jq_result.stderr}")
            return False

        print(f"Transcription completed for call ID: {self.callId}")
        os.remove(self.audio_filename)
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
            print(f"Error calculating total score: {str(e)}")
            return 0

    def run_step(self, step_name: str, step_function: callable) -> bool:
        print(f"{step_name} started for call ID: {self.callId}")
        result = step_function()
        if not result:
            print(f"Error: {step_name} failed for call ID: {self.callId}")
            return False

        print(f"{step_name} completed for call ID: {self.callId}")
        return True

    def updater(expert_id: str, expert_number: str) -> None:
        payload = json.dumps({
            "expert_id": expert_id,
            "expert_number": expert_number
        })
        headers = {'Content-Type': 'application/json'}
        response = requests.request("POST", url, headers=headers, data=payload)

        print(response.text)
