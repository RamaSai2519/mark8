from shared.db.events import get_events_collection, get_event_users_collection
from shared.db.users import get_user_collection, get_meta_collection
from shared.models.interfaces import FilterUsersByCohortInput as Input
from shared.db.experts import get_experts_collections
from shared.db.calls import get_calls_collection
from shared.models.constants import TimeFormats
from datetime import datetime, timedelta
from shared.models.common import Common


class FilterUsersByCohort:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.user_ids = []
        self.collection = get_user_collection()
        self.meta_collection = get_meta_collection()
        self.calls_collection = get_calls_collection()
        self.events_collection = get_events_collection()
        self.experts_collection = get_experts_collections()
        self.event_users_collection = get_event_users_collection()

    def handle_meta_filters(self) -> list:
        if not self.input.users_status:
            return self.user_ids
        query = {'userStatus': self.input.users_status}
        user_ids = self.meta_collection.distinct('user', query)
        return list(set(self.user_ids).intersection(user_ids))

    def get_expert_ids(self) -> list:
        query = {'type': self.input.call_with}
        expert_ids = self.experts_collection.distinct('_id', query)
        return expert_ids

    def handle_number_of_calls(self, user_ids: list) -> list:
        call_counts = {}
        query = {'user': {'$in': user_ids}}
        if self.input.call_type:
            query['status'] = self.input.call_type
        calls = self.calls_collection.find(query)
        for user_id in user_ids:
            call_counts[user_id] = 0

        for call in calls:
            user_id = call['user']
            if user_id in call_counts:
                call_counts[user_id] += 1

        call_count_map = {}
        for user_id, count in call_counts.items():
            if count not in call_count_map:
                call_count_map[count] = []
            if user_id not in call_count_map[count]:
                call_count_map[count].append(user_id)

        return call_count_map.get(self.input.number_of_calls, [])

    def handle_number_of_events(self, user_phones: list) -> list:
        event_counts = {}
        for phone in user_phones:
            query = {'phoneNumber': phone}
            event_counts[phone] = self.event_users_collection.count_documents(
                query)
        sorted_event_counts = dict(
            sorted(event_counts.items(), key=lambda item: item[1]))
        user_phones = list(sorted_event_counts.keys())[
            :self.input.number_of_events]
        query = {'phoneNumber': {'$in': user_phones}}
        user_ids = self.collection.distinct('_id', query)
        return user_ids

    def handle_call_filters(self) -> list:
        query = {}
        if self.input.call_with:
            expert_ids = self.get_expert_ids()
            query['expert'] = {'$in': expert_ids}

        if self.input.days_since_last_call:
            diff = timedelta(days=self.input.days_since_last_call)
            lower_bound = Common.get_current_utc_time() - diff
            lower_bound = lower_bound.replace(
                hour=0, minute=0, second=0, microsecond=0)
            upper_bound = lower_bound + timedelta(days=1)
            query['initiatedTime'] = {'$gte': lower_bound, '$lt': upper_bound}

        user_ids = self.calls_collection.distinct('user', query)

        if self.input.number_of_calls:
            user_ids = self.handle_number_of_calls(user_ids)

        return list(set(self.user_ids).intersection(user_ids))

    def handle_event_filters(self) -> list:
        query = {}
        if self.input.days_since_last_event:
            diff = timedelta(days=self.input.days_since_last_event)
            lower_bound = Common.get_current_utc_time() - diff
            lower_bound = lower_bound.replace(
                hour=0, minute=0, second=0, microsecond=0)
            upper_bound = lower_bound + timedelta(days=1)
            query['validUpto'] = {'$gte': lower_bound, '$lt': upper_bound}

        if self.input.event_id:
            query['slug'] = self.input.event_id

        slugs = self.events_collection.distinct('slug', query)
        query = {'source': {'$in': slugs}}
        user_phones = self.event_users_collection.distinct(
            'phoneNumber', query)
        query = {'phoneNumber': {'$in': user_phones}}

        user_ids = self.collection.distinct('_id', query)
        if self.input.number_of_events:
            user_ids = self.handle_number_of_events(user_phones)

        return list(set(self.user_ids).intersection(user_ids))

    def get_user_ids(self) -> list:
        users_query = {'wa_opt_out': False}
        if self.input.users_type:
            if self.input.users_type == 'leads':
                users_query = {"profileCompleted": False}
            elif self.input.users_type == 'users':
                users_query = {"profileCompleted": True}

        if self.input.join_date_start and self.input.join_date_end:
            fields = ['join_date_start', 'join_date_end']
            for field in fields:
                if isinstance(getattr(self.input, field), str):
                    setattr(self.input, field, datetime.strptime(
                        getattr(self.input, field), TimeFormats.ANTD_TIME_FORMAT))

            users_query['createdDate'] = {
                '$gte': self.input.join_date_start,
                '$lte': self.input.join_date_end
            }

        if self.input.cities:
            users_query['city'] = {'$in': self.input.cities}

        self.user_ids = self.collection.distinct('_id', users_query)
        print(len(self.user_ids), 'After user filters')

        self.user_ids = self.handle_meta_filters()
        print(len(self.user_ids), 'After meta filters')

        if any([self.input.call_with, self.input.days_since_last_call, self.input.number_of_calls]):
            self.user_ids = self.handle_call_filters()
            print(len(self.user_ids), 'After call filters')

        if any([self.input.days_since_last_event, self.input.event_id, self.input.number_of_events]):
            self.user_ids = self.handle_event_filters()
            print(len(self.user_ids), 'After event filters')

        return self.user_ids
