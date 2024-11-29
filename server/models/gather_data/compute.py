from shared.models.interfaces import GatherDataInput as Input, Output
from shared.db.admins import get_error_logs_collection
from shared.models.constants import OutputStatus
from shared.configs import CONFIG as Config
import requests
import time


class Compute:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.logs_collection = get_error_logs_collection()

    def fetch_enagement_data(self, params: dict) -> dict:
        url = Config.URL + "/actions/user_engagement"
        bearer = "Bearer " + Config.GAMES_ACCESS_TOKEN
        headers = {"Authorization": bearer}
        response = requests.get(url, params=params, headers=headers)
        response = response.json()
        if not response.get("output_status"):
            print(response)
            raise Exception("Failed to fetch data")

        output = response.get("output_details")
        return output

    def gather_engagement_data(self) -> list:
        total = 0
        final_data = []
        params = {"size": 10, "page": 1}

        output = self.fetch_enagement_data(params)
        total = output.get("total")
        final_data.extend(output.get("data"))
        total_pages = total // params["size"]
        message = "{current}/{total} pages fetched"

        while len(final_data) < total:
            params["page"] += 1
            output = self.fetch_enagement_data(params)
            data = output.get("data")
            final_data.extend(data)
            page = params["page"]
            print(message.format(current=page, total=total_pages))
            time.sleep(1)
        return final_data

    def upload_file(self, data: list[dict]) -> str:
        url = Config.MARK_URL + "/flask/excel_upload"
        payload = {"data": data, "file_name": self.input.file_name}
        response = requests.post(url, json=payload)
        response: dict = response.json()
        print(response)

        file_url = response.get("output_details").get("file_url")
        return file_url

    def mark_as_done(self):
        query = {"data_type": {"$exists": True}}
        self.logs_collection.delete_many(query)

    def compute(self) -> Output:
        if self.input.data_type == "engagement":
            data = self.gather_engagement_data()
            file_url = self.upload_file(data)
            self.mark_as_done()
            return Output(
                output_details={"file_url": file_url},
                output_status=OutputStatus.SUCCESS,
                output_message="Engagement data fetched successfully"
            )

        return Output(
            output_status=OutputStatus.SUCCESS,
            output_message="No data fetched"
        )
