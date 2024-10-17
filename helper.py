import os
import re
import json
import requests
import subprocess
from config import DEEPGRAM_API_KEY
from urllib.parse import urlparse, ParseResult


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
            with open("guidelines.txt", "r", encoding="utf-8") as file:
                guidelines = file.read()
        else:
            with open("guidelines2.txt", "r", encoding="utf-8") as file:
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
