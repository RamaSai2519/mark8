import re
from notify import notify
from prompts import Prompts
from helper import ProcessorHelper
from json_extractor import extract_json
from interfaces import CallProcessorOutput, Constants
from config import open_ai_client as client

user = Constants.user

class CallProcessor:
    def __init__(self, call_document, user_name, expert_name, user_persona, user_calls_count) -> None:
        # Input data
        self.user_name = user_name
        self.expert_name = expert_name
        self.call_document = call_document
        self.callId = call_document["callId"]
        self.user_calls_count = user_calls_count
        self.audio_filename = f"{self.callId}.mp3"
        self.old_persona = user_persona if user_persona != "None" else None

        self.helper

        # Output data
        self.output = CallProcessorOutput()
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
        guidelines = self.get_guidelines()
        prompts = Prompts.get_evaluation_prompts(guidelines)
        user_callback = self.chat(user, prompts.callback_prompt)
        summary = self.chat(user, prompts.summary_prompt)
        saarthi_feedback = self.chat(user, prompts.feedback_prompt)
        conversation_score_details = self.chat(
            user, prompts.score_details_prompt)

        conversation_score_raw = self.chat(user, prompts.score_prompt)
        conversation_score = self.extract_score(conversation_score_raw)

        self.output = CallProcessorOutput(
            **self.output.__dict__, summary=summary, user_callback=user_callback,
            saarthi_feedback=saarthi_feedback, conversation_score=conversation_score,
            conversation_score_details=conversation_score_details
        )

    def identify_topics(self) -> None:
        with open("topics.txt", "r", encoding="utf-8") as file:
            topics = file.read()
        prompt = Prompts.get_topics_prompt(topics)
        topics = self.chat(user, prompt)

        self.output = CallProcessorOutput(**self.output.__dict__, topics=topics)

    def generate_persona(self) -> None:
        prompt = Prompts.get_persona_prompt(self.old_persona)
        customer_persona = self.chat(user, prompt)

        self.output = CallProcessorOutput(**self.output.__dict__, customer_persona=customer_persona)

    def process_call(self) -> CallProcessorOutput | None:
        print(f"Starting process for call ID: {self.call_document['callId']}")
        self.output


        if not self.analyze_transcript():
            return None

        self.evaluate_call()
        self.identify_topics()
        self.generate_persona()

        return self.output


def process_call_recording(document, user, expert, persona, user_calls):
    processor = CallProcessor(document, user, expert, persona, user_calls)
    return processor.process_call()
