from server.models.chat.helpers.wa_chat_helper import WaChatHelper
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
        self.embedder = Embedder(self.input.context)
        self.histories_collection = get_histories_collection()
        self.wa_chat_helper = WaChatHelper(self.input.phoneNumber)

        self.now_date = self.get_now_date()
        self.query = self.prep_query()
        self.message_history, self.history_id, self.system_message = self.determine_history()
        self.system_embedding = self.embedder.get_embedding(
            self.system_message)

    def get_helper(self):
        if self.input.context == 'wa_webhook':
            return self.wa_chat_helper

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
            return history['history'], history['_id'], history['history'][-1]['content']

        helper = self.get_helper()
        if not helper:
            system_message = "You are a helpful AI assistant."
            default_history = [{"role": "system", "content": system_message}]
        else:
            system_message = helper.get_system_message()
            default_history = [{"role": "system", "content": system_message}]

        insertion = self.histories_collection.insert_one(
            {**self.query, 'history': default_history, 'status': 'started'})
        return default_history, insertion.inserted_id, system_message

    def update_history(self, role: str, content: str) -> None:
        self.message_history.append(
            {"role": role, "content": content, "timestamp": Common.get_current_utc_time().strftime('%Y-%m-%d %H:%M:%S')})
        return self.message_history

    def save_history(self) -> None:
        update = {'$set': {'history': self.message_history, 'status': 'done'}}
        self.histories_collection.update_one({'_id': self.history_id}, update)

    def truncate_history(self):
        system_message = self.message_history[0]
        truncated_history = [system_message]
        self.message_history = truncated_history
        self.update_history('user', self.input.prompt)

    def get_gpt_response(self) -> str:
        client_obj = GPT_Client()
        client = client_obj.get_gpt_client()
        tools = self.get_helper().get_tools()
        errors = 0
        while True:
            try:
                response = client.chat.completions.create(
                    model='gpt-4-turbo', messages=self.message_history, tools=tools)
                tool_calls = response.choices[0].message.tool_calls
                if tool_calls:
                    self.message_history.append({
                        'role': 'assistant',
                        'tool_calls': [
                            {**t.__dict__, 'function': t.function.__dict__}
                            for t in tool_calls
                        ],
                    })
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        arguments = tool_call.function.arguments
                        tool_response = self.get_helper().handle_function_call(
                            function_name, arguments)
                        self.message_history.append(
                            {'role': 'tool', 'content': tool_response, 'tool_call_id': tool_call.id, 'timestamp': Common.get_current_utc_time().strftime('%Y-%m-%d %H:%M:%S')})
                    continue
                break
            except RateLimitError:
                print('Rate limit error. Waiting for 5 seconds.')
                errors += 1
                if errors > 3:
                    print('Truncating message history.')
                    self.truncate_history()
                    continue
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

        if self.input.use_embedder == False or self.input.context == 'wa_webhook':
            response = self.get_gpt_response()
        else:
            embedding = self.embedder.get_embedding(self.input.prompt)
            embeddings = [self.system_embedding, embedding]
            concated_embedding = np.concatenate(embeddings).tolist()
            similar_entry = self.embedder.get_most_similar_prompt(
                concated_embedding)
            if similar_entry:
                response = similar_entry['response']
            else:
                response = self.get_gpt_response()
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
