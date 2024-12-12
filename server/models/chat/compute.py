from shared.models.interfaces import ChatInput as Input, Output
from shared.db.chat import get_histories_collection
from server.models.chat.embedder import Embedder
from shared.helpers.openai import GPT_Client
from shared.models.common import Common
from openai import RateLimitError
from datetime import datetime
import numpy as np
import time


class Compute:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.common = Common()
        self.system_embedding = None
        self.embedder = Embedder(self.input.context)
        self.histories_collection = get_histories_collection()

        self.now_date = self.get_now_date()
        self.query = self.prep_query()
        self.message_history, self.history_id = self.determine_history()

    def get_now_date(self) -> datetime:
        now_date = Common.get_current_utc_time()
        now_date = now_date.strftime('%Y-%m-%d %H')
        return now_date

    def prep_query(self) -> dict:
        query = {'phoneNumber': self.input.phoneNumber,
                 'createdAt': self.now_date, 'context': self.input.context}
        return query

    def determine_history(self) -> tuple[list[dict], str]:
        history = self.histories_collection.find_one(self.query)
        if history:
            return history['history'], history['_id']

        default_history = [
            {"role": "system", "content": self.input.system_message or "You are a helpful AI assistant."}]
        insertion = self.histories_collection.insert_one(
            {**self.query, 'history': default_history, 'status': 'started'})
        return default_history, insertion.inserted_id

    def update_history(self, role: str, content: str) -> None:
        self.message_history.append(
            {"role": role, "content": content, "timestamp": datetime.now()})
        return self.message_history

    def save_history(self) -> None:
        update = {'$set': {'history': self.message_history, 'status': 'done'}}
        self.histories_collection.update_one({'_id': self.history_id}, update)

    def get_gpt_response(self, format: dict = None) -> str:
        client_obj = GPT_Client()
        client = client_obj.get_gpt_client()
        while True:
            try:
                if format:
                    response = client.beta.chat.completions.parse(
                        model='gpt-4-turbo', messages=self.message_history, response_format=format)
                else:
                    response = client.chat.completions.create(
                        model='gpt-4-turbo', messages=self.message_history)
                break
            except RateLimitError:
                time.sleep(5)

        assistant_response = response.choices[0].message.content
        return assistant_response

    def check_to_serve(self) -> bool:
        doc = self.histories_collection.find_one(self.query)
        if doc['status'] == 'inprogress':
            return False
        update = {'$set': {'status': 'inprogress'}}
        self.histories_collection.update_one({'_id': self.history_id}, update)
        return True

    def compute(self) -> Output:
        if self.check_to_serve() == False:
            return Output(output_message='Please wait for the assistant to respond.')
        self.update_history('user', self.input.prompt)
        self.system_embedding = self.embedder.get_embedding(
            self.input.system_message)

        if self.input.use_embedder == False:
            response = self.get_gpt_response(self.input.res_format)
        else:
            embedding = self.embedder.get_embedding(self.input.prompt)
            embeddings = [self.system_embedding, embedding]
            concated_embedding = np.concatenate(embeddings).tolist()
            similar_entry = self.embedder.get_most_similar_prompt(
                concated_embedding)
            if similar_entry:
                response = similar_entry['response']
            else:
                response = self.get_gpt_response(self.input.res_format)
                self.embedder.store_embedding(
                    self.input.prompt, concated_embedding, response)

        self.update_history('assistant', response)
        self.save_history()

        return Output(
            output_details={
                'response': Common.jsonify(response),
                'history': Common.jsonify(self.message_history)
            }
        )
