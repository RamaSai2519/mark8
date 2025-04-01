import requests
import threading
import pandas as pd
from datetime import datetime
from shared.models.common import Common
from shared.configs import CONFIG as config
from shared.db.users import get_user_collection, get_meta_collection
from shared.models.interfaces import BulkUploadInput as Input, Output, User


class Compute:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.users_collection = get_user_collection()
        self.meta_collection = get_meta_collection()

    def load_data(self) -> pd.DataFrame:
        data = pd.read_csv(self.input.file_url)
        return data.to_dict(orient='records')

    def get_default(self) -> dict:
        user = User(
            isBusy=False, active=True, profileCompleted=False
        ).__dict__
        user = Common.filter_none_values(user)
        return user

    def __format__(self, record: dict) -> dict:
        user = self.get_default()
        user['name'] = str(str(record["First Name"]) + " " +
                           str(record["Last Name"])).strip()
        user['email'] = str(record.get("Email", "")).strip()

        try:
            user_joined_date = datetime.strptime(
                str(record["Registration Time"]), "%m/%d/%Y %I:%M:%S %p")
            user['createdDate'] = user_joined_date
        except:
            pass

        try:
            birthDate = datetime.strptime(
                str(record['date_of_birth']), "%m/%d/%Y")
            user['birthDate'] = birthDate
        except:
            pass

        user["phoneNumber"] = str(record["Phone"]).replace('.0', '')
        user['refSource'] = str(record.get("ref", "")).strip()
        user['city'] = str(record.get("city", "")).strip()

        return user

    def insert_user(self, user: dict) -> str:
        url = config.URL + '/actions/user'
        response = requests.post(url, json=user)
        if response.status_code != 200:
            print(f"Failed to insert user: {response.text}")
            return None
        return response.json().get("output_details", {}).get("_id", "")

    def insert_meta(self, user_id: str, record: dict) -> None:
        meta = {
            'remarks': '',
            'user': user_id,
            'userStatus': '',
            'context': str(record.get("Webinar", "")).strip(),
            'source': str(record.get("ref", "")).strip(),
        }
        insertion = self.meta_collection.insert_one(meta)
        return insertion.inserted_id

    def insert_users(self, data: pd.DataFrame) -> None:
        for record in data:
            user = self.__format__(record)
            inserted_id = self.insert_user(Common.jsonify(user))
            if not inserted_id:
                continue

            try:
                self.insert_meta(inserted_id, record)
            except:
                pass

    def compute(self) -> Output:
        data = self.load_data()
        threading.Thread(
            target=self.insert_users,
            args=(data,)
        ).start()
        return Output(
            output_message=f"Hojayega"
        )
