from shared.models.interfaces import SendFCMMsgsInput as Input, Output, FilterUsersByCohortInput
from shared.db.users import get_user_collection, get_user_fcm_token_collection
from server.models.common import FilterUsersByCohort
from firebase_admin import credentials, messaging
from shared.models.constants import OutputStatus
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

    def broadcast_message(self, tokens: list[dict], body: str, title: str, image_url: str) -> None:
        self.initialize_firebase_admin()
        messages = []
        for token in tokens:
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

        response = messaging.send_each(messages)
        print(response.success_count, 'Success Count')
        print(response.failure_count, 'Failure Count')

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
                output_status=OutputStatus.SUCCESS,
                output_message='Preview generated successfully'
            )

        query['user'] = query['_id']
        del query['_id']
        tokens_docs = list(self.fcm_collection.find(query))
        tokens = []
        for doc in tokens_docs:
            tokens.extend([token['token'] for token in doc['tokens']])

        self.broadcast_message(
            tokens, self.input.body, self.input.title, self.input.image_url)

        return Output(
            output_message='Messages queued successfully'
        )
