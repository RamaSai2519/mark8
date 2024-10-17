from helper import Helper
from prompts import Prompts
from config import open_ai_client as client
from interfaces import AnalyserOutput, Constants

user = Constants.user


class Analyser:
    def __init__(self, call_document: dict, user_name: str, expert_name: str, user_persona: str, user_calls_count: int) -> None:
        # Input data
        self.user_name = user_name
        self.expert_name = expert_name
        self.call_document = call_document
        self.callId = call_document["callId"]
        self.user_calls_count = user_calls_count
        self.audio_filename = f"{self.callId}.mp3"
        self.old_persona = user_persona if user_persona != "None" else None

        # Output data
        self.helper = Helper(
            self.callId, self.audio_filename, call_document["recording_url"], user_calls_count)
        self.output = AnalyserOutput()
        self.message_history = [
            {"role": "system", "content": "You are a helpful assistant."}]

    def chat(self, role, content) -> str | None:
        self.message_history.append({"role": role, "content": content})
        response = client.chat.completions.create(
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
        with open("topics.txt", "r", encoding="utf-8") as file:
            topics = file.read()
        prompt = Prompts.get_topics_prompt(topics)
        topics = self.chat(user, prompt)
        self.output.topics = self.helper.extract_json(topics)

    def generate_persona(self) -> None:
        prompt = Prompts.get_persona_prompt(self.old_persona)
        customer_persona = self.chat(user, prompt)
        self.output.customer_persona = self.helper.extract_json(
            customer_persona)

    def process_call(self) -> AnalyserOutput | None:
        print(f"Starting process for call ID: {self.call_document['callId']}")
        self.output.transcript = self.helper.download_and_transcribe_audio()
        if not self.output.transcript:
            return None

        if not self.analyze_transcript():
            return None

        self.evaluate_call()
        self.identify_topics()
        self.generate_persona()

        return self.output
