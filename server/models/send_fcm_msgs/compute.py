from shared.models.interfaces import SendFCMMsgsInput as Input, Output, FilterUsersByCohortInput
from shared.db.users import get_user_collection, get_user_fcm_token_collection
from server.models.common import FilterUsersByCohort
from firebase_admin import credentials, messaging
from shared.models.common import Common
import firebase_admin
import os


class Compute:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.user_ids = []
        self.collection = get_user_collection()
        self.fcm_collection = get_user_fcm_token_collection()

    def initialize_firebase_admin(self) -> None:
        file_path = os.path.join(os.path.dirname(
            __file__), 'user-service-account.json')

        if not firebase_admin._apps:
            cred = credentials.Certificate(file_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://games-sukoon-app-default-rtdb.firebaseio.com'
            })

    def broadcast_message(self, tokens: list[str], body: str, title: str, image_url: str) -> dict:
        self.initialize_firebase_admin()
        messages = []
        for token in tokens:
            if not token:
                continue
            messages.append(
                messaging.Message(
                    token=token,
                    notification=messaging.Notification(
                        body=body,
                        image=image_url,
                        title=title
                    )
                )
            )

        output = {'success': 0, 'failure': 0}

        if len(messages) > 500:
            for i in range(0, len(messages), 500):
                batch = messages[i:i + 500]
                response = messaging.send_each(batch)
                output['success'] += response.success_count
                output['failure'] += response.failure_count
        else:
            response = messaging.send_each(messages)
            output['success'] += response.success_count
            output['failure'] += response.failure_count

        return output

    def compute(self) -> Output:
        cohorts_input = Common.clean_dict(
            self.input.__dict__, FilterUsersByCohortInput)
        cohorts_input = FilterUsersByCohortInput(**cohorts_input)
        cohorts_filter = FilterUsersByCohort(cohorts_input)
        self.user_ids = cohorts_filter.get_user_ids()
        query = {'_id': {'$in': self.user_ids}}
        if self.input.action == 'preview':
            users_count = self.collection.count_documents(query)
            return Output(
                output_details={'count': users_count},
                output_message='Preview generated successfully'
            )

        query['user'] = query['_id']
        del query['_id']
        tokens_docs = list(self.fcm_collection.find(query))
        tokens = []
        for doc in tokens_docs:
            tokens.extend([token['token'] for token in doc['tokens']])

        response_data = self.broadcast_message(
            tokens, self.input.body, self.input.title, self.input.image_url)

        return Output(
            output_details=response_data,
            output_message='Notified Users Successfully' + str(response_data)
        )
