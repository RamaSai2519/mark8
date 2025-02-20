import json
import time
import numpy as np
from mark.vector import Embedder
from openai import RateLimitError
from mark.helper import Helper, log
from mark.helper.prompts import Prompts
from shared.helpers.openai import GPT_Client
from shared.schemas import JsonPrompts, UserInterest
from shared.models.interfaces import AnalyserOutput, Constants, Step

user = Constants.user
assistant = Constants.assistant


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

        self.embedder = Embedder()
        self.gpt_client = GPT_Client().get_gpt_client()
        self.helper = Helper(self.callId, self.audio_filename,
                             call_document["recording_url"], user_calls_count)
        self.output = AnalyserOutput()
        self.transcript_embedding = None
        self.message_history = [
            {"role": "system", "content": "You are a helpful assistant."}]

    def get_gpt_response(self, format: dict = None) -> str:
        response = self.gpt_client
        while True:
            try:
                if format:
                    response = response.beta.chat.completions.parse(
                        model="gpt-4o-2024-11-20", messages=self.message_history, response_format=format)
                else:
                    response = response.chat.completions.create(
                        model="gpt-4o-2024-11-20", messages=self.message_history)
                break
            except RateLimitError:
                time.sleep(5)

        assistant_response = response.choices[0].message.content
        return assistant_response

    def update_history(self, role: str, content: str) -> None:
        self.message_history.append({"role": role, "content": content})
        return self.message_history

    def chat(self, content: str | JsonPrompts, contexter: bool = False, role: str = user) -> str | None:
        res_format = None
        if isinstance(content, JsonPrompts):
            content, res_format = content.prompt, content.rformat

        self.update_history(role, content)
        if contexter:
            response = self.get_gpt_response(res_format)
            self.update_history(assistant, response)
            return response
        prompt_embedding = self.embedder.get_prompt_embedding(content)
        embeddings = [self.transcript_embedding, prompt_embedding]
        concated_embedding = np.concatenate(embeddings).tolist()
        similar_entry = self.embedder.get_most_similar_prompt(
            concated_embedding, content)
        if similar_entry:
            self.update_history(assistant, similar_entry["response"])
            return similar_entry["response"]

        response = self.get_gpt_response(res_format)
        self.embedder.store_embedding(content, concated_embedding, response)
        self.update_history(assistant, response)
        return response

    def analyze_transcript(self) -> bool:
        prompts = Prompts.get_transcript_prompts(
            self.user_name, self.expert_name, self.output.transcript)
        self.chat(prompts.init_prompt, True)
        self.chat(prompts.transcript_prompt, True)

        analysis_result = self.chat(prompts.analysis_prompt, True)

        if "all good" in analysis_result.lower():
            self.output.inappropiate_content = None
            return True
        log(self.callId, "Inappropriate content found")
        log(self.callId, f"Analysis result: {analysis_result}")
        self.output.inappropiate_content = analysis_result
        return True

    def create_step(self, description: str, method: callable) -> dict:
        return Step(description, method)

    def evaluate_call(self) -> None:
        guidelines = self.helper.get_guidelines()
        prompts = Prompts.get_evaluation_prompts(guidelines)

        def give_guidelines() -> str:
            return self.chat(prompts.guidelines_prompt)

        def get_user_callback() -> str:
            self.output.user_callback = self.chat(prompts.callback_prompt)
            return self.output.user_callback

        def get_summary() -> str:
            self.output.summary = self.chat(prompts.summary_prompt)
            return self.output.summary

        def get_feedback() -> str:
            self.output.saarthi_feedback = self.chat(prompts.feedback_prompt)
            return self.output.saarthi_feedback

        def get_score_details() -> dict:
            score_details = self.chat(prompts.score_details_prompt)
            self.output.score_details = json.loads(score_details)
            return self.output.score_details

        def get_score() -> float:
            raw_score = self.chat(prompts.score_prompt)
            raw_score = json.loads(raw_score)
            score = raw_score.get('score', 0)
            if score < 0:
                score = 0
            else:
                score = int(score) / 20
                score = round(score, 2)
            self.output.score = score
            return str(self.output.score)

        steps: list[Step] = [
            self.create_step("Giving guidelines", give_guidelines),
            self.create_step("Getting callback", get_user_callback),
            self.create_step("Getting summary", get_summary),
            self.create_step("Getting feedback", get_feedback),
            self.create_step("Getting score details", get_score_details),
            self.create_step("Getting score", get_score),
        ]

        for step in steps:
            if not self.helper.run_step(step.description, step.method):
                return None

        return str(self.output.score)

    def identify_topics(self) -> None:
        topics_file = Helper.get_file_path("mark/texts/topics.txt")
        with open(topics_file, "r", encoding="utf-8") as file:
            topics = file.read()
        prompt = Prompts.get_topics_prompt(topics)
        topics = self.chat(prompt)

        self.output.topics = json.loads(topics)['topics']
        return str(self.output.topics)

    def generate_personas(self) -> None:
        def get_user_persona() -> str:
            prompt = Prompts.get_persona_prompt(self.old_user_persona)
            customer_persona = self.chat(prompt)
            self.output.customer_persona = json.loads(customer_persona)
            return str(self.output.customer_persona)

        def get_expert_persona() -> str:
            prompt = Prompts.get_persona_prompt(
                self.old_expert_persona, "sarathi")
            expert_persona = self.chat(prompt)
            self.output.expert_persona = json.loads(expert_persona)
            return str(self.output.expert_persona)

        steps: list[Step] = [
            self.create_step("Generating user persona", get_user_persona),
            self.create_step("Generating expert persona", get_expert_persona),
        ]

        for step in steps:
            if not self.helper.run_step(step.description, step.method):
                return None

        return str(self.output.customer_persona)

    def generate_transcript(self) -> str:
        self.output.transcript = self.helper.download_and_transcribe_audio()
        if not self.output.transcript:
            return None
        self.transcript_embedding = self.embedder.get_transcript_embedding(
            self.output.transcript)
        return self.output.transcript

    def check_interest(self) -> str:
        prompt = Prompts.get_interest_prompt()
        user_interest = self.chat(prompt, True)
        user_interest = json.loads(user_interest)
        self.output.user_interest = UserInterest(**user_interest)
        return user_interest

    def process_call(self) -> AnalyserOutput | None:
        start_message = "Starting process for call with:\n CallId: {callId}\n User: {user_name}\n Expert: {expert_name}"
        start_message = start_message.format(
            callId=self.callId, user_name=self.user_name, expert_name=self.expert_name)
        log(self.callId, start_message)

        steps: list[Step] = [
            self.create_step("Audio to Text", self.generate_transcript),
            self.create_step("Analyzing transcript", self.analyze_transcript),
            self.create_step("Evaluating call", self.evaluate_call),
            self.create_step("Identifying topics", self.identify_topics),
            self.create_step("Generating personas", self.generate_personas),
            self.create_step("Checking interest", self.check_interest)
        ]

        for step in steps:
            if not self.helper.run_step(step.description, step.method):
                return None

        return self.output
