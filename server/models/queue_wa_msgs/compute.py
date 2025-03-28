from shared.models.interfaces import QueueWaMsgsInput as Input, Output, FilterUsersByCohortInput
from server.models.common import FilterUsersByCohort
from shared.models.constants import OutputStatus
from shared.db.users import get_user_collection
from shared.models.constants import TimeFormats
from shared.configs import CONFIG as config
from shared.models.common import Common
from datetime import timedelta
import requests
import time


class Compute:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.user_ids = []
        self.collection = get_user_collection()

    def prep_payload(self, user: dict) -> dict:
        params = self.input.params
        if params.get('user_name'):
            params['user_name'] = user.get('name', 'User')

        payload = {
            'template_name': self.input.template,
            'phone_number': user.get('phoneNumber'),
            'parameters': params,
            'request_meta': 'queue_wa_msgs'
        }
        return {
            'initiatedBy': self.input.initiatedBy,
            'job_type': 'WA',
            'payload': payload,
            'status': 'PENDING',
            'job_time': (Common.get_current_utc_time() + timedelta(minutes=1)).strftime(TimeFormats.AWS_TIME_FORMAT),
            'user_requested': False
        }

    def compute(self) -> Output:
        cohorts_input = Common.clean_dict(
            self.input.__dict__, FilterUsersByCohortInput)
        cohorts_input = FilterUsersByCohortInput(**cohorts_input)
        cohorts_filter = FilterUsersByCohort(cohorts_input)
        self.user_ids = cohorts_filter.get_user_ids()
        print(self.user_ids, 'Final user ids')
        query = {'_id': {'$in': self.user_ids}}
        if self.input.action == 'preview':
            users_count = self.collection.count_documents(query)
            return Output(
                output_details={'count': users_count},
                output_status=OutputStatus.SUCCESS,
                output_message='Preview generated successfully'
            )

        projection = {'_id': 1, 'phoneNumber': 1, 'name': 1}
        users = self.collection.find(query, projection)
        for user in users:
            payload = self.prep_payload(user)
            url = config.URL + '/actions/schedules'
            response = requests.post(url, json=payload)
            response = response.json()
            print(response, 'Response from scheduling')
            if not response.get('output_status'):
                print(response, 'Failed to schedule job')
            print('Scheduled WA text for', user.get(
                'name', user.get('phoneNumber')))
            time.sleep(1)

        return Output(
            output_message='Messages queued successfully'
        )
