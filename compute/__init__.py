import time
from helper import Helper, log
from helper.prompts import Prompts
from openai import AzureOpenAI, RateLimitError
from interfaces import AnalyserOutput, Constants
from config import GPT_ENDPOINT, GPT_API_KEY, GPT_VERSION, ADA_API_KEY, ADA_VERSION, ADA_ENDPOINT

user = Constants.user


class Compute:
    def __init__(self, call_document: dict, user_name: str, expert_name: str, user_persona: str, user_calls_count: int, expert_persona: str) -> None:
        self.user_name = user_name
        self.expert_name = expert_name
        self.call_document = call_document
        self.old_user_persona = user_persona
        self.callId = call_document["callId"]
        self.old_expert_persona = expert_persona
        self.user_calls_count = user_calls_count
        self.audio_filename = f"{self.callId}.mp3"

        self.gpt_client = AzureOpenAI(
            azure_endpoint=GPT_ENDPOINT, api_key=GPT_API_KEY, api_version=GPT_VERSION)
        self.ada_client = AzureOpenAI(
            azure_endpoint=ADA_ENDPOINT, api_key=ADA_API_KEY, api_version=ADA_VERSION)
        self.helper = Helper(
            self.callId, self.audio_filename, call_document["recording_url"], user_calls_count)
        self.output = AnalyserOutput()
        self.message_history = [
            {"role": "system", "content": "You are a helpful assistant."}]

    def chat(self, role, content) -> str | None:
        self.message_history.append({"role": role, "content": content})

        try:
            response = self.gpt_client.chat.completions.create(
                model="gpt-4-turbo", messages=self.message_history)
        except RateLimitError:
            time.sleep(5)
            response = self.gpt_client.chat.completions.create(
                model="gpt-4-turbo", messages=self.message_history)

        assistant_response = response.choices[0].message.content
        self.message_history.append(
            {"role": "assistant", "content": assistant_response})
        return assistant_response

    def analyze_transcript(self) -> bool:
        prompts = Prompts.get_transcript_prompts(
            self.user_name, self.expert_name, self.output.transcript)
        self.chat(user, prompts.init_prompt)
        self.chat(user, prompts.transcript_prompt)

        analysis_result = self.chat(user, prompts.analysis_prompt)

        if "All good" in analysis_result:
            return True
        log(self.callId, "Inappropriate content found")
        log(self.callId, f"Analysis result: {analysis_result}")
        raise Exception("Inappropriate content found")

    def evaluate_call(self) -> None:
        guidelines = self.helper.get_guidelines()
        prompts = Prompts.get_evaluation_prompts(guidelines)

        self.output.user_callback = self.chat(user, prompts.callback_prompt)
        self.output.summary = self.chat(user, prompts.summary_prompt)
        self.output.saarthi_feedback = self.chat(user, prompts.feedback_prompt)

        score_details = self.chat(user, prompts.score_details_prompt)
        score_details = self.helper.extract_json(score_details)
        self.output.conversation_score_details = score_details

        raw_score = self.chat(user, prompts.score_prompt)
        self.output.conversation_score = self.helper.extract_score(raw_score)

        return self.output.conversation_score

    def identify_topics(self) -> None:
        topics_file = Helper.get_file_path("texts/topics.txt")
        with open(topics_file, "r", encoding="utf-8") as file:
            topics = file.read()
        prompt = Prompts.get_topics_prompt(topics)
        topics = self.chat(user, prompt)
        self.output.topics = self.helper.extract_json(topics)
        return self.output.topics

    def generate_personas(self) -> None:
        prompt = Prompts.get_persona_prompt(self.old_user_persona)
        customer_persona = self.chat(user, prompt)
        self.output.customer_persona = self.helper.extract_json(
            customer_persona)

        prompt = Prompts.get_persona_prompt(self.old_expert_persona, "sarathi")
        expert_persona = self.chat(user, prompt)
        self.output.expert_persona = self.helper.extract_json(expert_persona)

        return self.output.customer_persona

    def generate_transcript(self) -> str:
        self.output.transcript = self.helper.download_and_transcribe_audio()
        return self.output.transcript

    def process_call(self) -> AnalyserOutput | None:
        start_message = "Starting process for call with:\n CallId: {callId}\n User: {user_name}\n Expert: {expert_name}"
        start_message = start_message.format(
            callId=self.callId, user_name=self.user_name, expert_name=self.expert_name)
        log(self.callId, start_message)

        steps = [
            {"description": "Downloading and transcribing audio",
                "method": self.generate_transcript},
            {"description": "Analyzing transcript",
                "method": self.analyze_transcript},
            {"description": "Evaluating call", "method": self.evaluate_call},
            {"description": "Identifying topics", "method": self.identify_topics},
            {"description": "Generating personas",
                "method": self.generate_personas},
        ]

        for step in steps:
            if not self.helper.run_step(step["description"], step["method"]):
                return None

        return self.output
