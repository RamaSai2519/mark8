from helper import Helper
from openai import AzureOpenAI
from helper.prompts import Prompts
from interfaces import AnalyserOutput, Constants
from config import  OPEN_AI_VERSION, OPENAI_API_KEY, AZURE_ENDPOINT

user = Constants.user


class Compute:
    def __init__(self, call_document: dict, user_name: str, expert_name: str, user_persona: str, user_calls_count: int) -> None:
        self.user_name = user_name
        self.expert_name = expert_name
        self.call_document = call_document
        self.callId = call_document["callId"]
        self.user_calls_count = user_calls_count
        self.audio_filename = f"{self.callId}.mp3"
        self.old_persona = user_persona if user_persona != "None" else None

        self.client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT, api_key=OPENAI_API_KEY, api_version=OPEN_AI_VERSION)
        self.helper = Helper(
            self.callId, self.audio_filename, call_document["recording_url"], user_calls_count)
        self.output = AnalyserOutput()
        self.message_history = [
            {"role": "system", "content": "You are a helpful assistant."}]

    def chat(self, role, content) -> str | None:
        self.message_history.append({"role": role, "content": content})
        response = self.client.chat.completions.create(
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
        print(f"Inappropriate content found for call ID: {self.callId}")
        return False

    def evaluate_call(self) -> None:
        guidelines = self.helper.get_guidelines()
        prompts = Prompts.get_evaluation_prompts(guidelines)

        self.output.user_callback = self.chat(user, prompts.callback_prompt)
        self.output.summary = self.chat(user, prompts.summary_prompt)
        self.output.saarthi_feedback = self.chat(user, prompts.feedback_prompt)

        score_details = self.chat(user, prompts.score_details_prompt)
        score_details = self.helper.extract_json(score_details)

        raw_score = self.chat(user, prompts.score_prompt)
        self.output.conversation_score = self.helper.extract_score(raw_score)

    def identify_topics(self) -> None:
        with open("texts/topics.txt", "r", encoding="utf-8") as file:
            topics = file.read()
        prompt = Prompts.get_topics_prompt(topics)
        topics = self.chat(user, prompt)
        self.output.topics = self.helper.extract_json(topics)

    def generate_persona(self) -> None:
        prompt = Prompts.get_persona_prompt(self.old_persona)
        customer_persona = self.chat(user, prompt)
        self.output.customer_persona = self.helper.extract_json(
            customer_persona)

    def generate_transcript(self) -> str:
        self.output.transcript = self.helper.download_and_transcribe_audio()

    def process_call(self) -> AnalyserOutput | None:
        print(f"Starting process for call ID: {self.callId}")

        steps = [
            {"description": "Downloading and transcribing audio", "method": self.generate_transcript},
            {"description": "Analyzing transcript", "method": self.analyze_transcript},
            {"description": "Evaluating call", "method": self.evaluate_call},
            {"description": "Identifying topics", "method": self.identify_topics},
            {"description": "Generating persona", "method": self.generate_persona},
        ]

        for step in steps:
            if not self.helper.run_step(step["description"], step["method"]):
                return None 

        return self.output
