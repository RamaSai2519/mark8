import json
import dataclasses
from flask import request
from flask_restful import Resource
from server.models.gather_data.main import GatherData
from server.models.queue_wa_msgs.main import QueueWaMsgs
from server.models.send_fcm_msgs.main import SendFCMMsgs
from server.models.bulk_insert_users.main import BulkInsertUsers
from shared.models.interfaces import GatherDataInput, QueueWaMsgsInput, SendFCMMsgsInput, BulkUploadInput


class GatherDataService(Resource):

    def get(self) -> dict:
        input_params = request.args
        input = GatherDataInput(**input_params)
        output = GatherData(input).process()
        output = dataclasses.asdict(output)

        return output


class QueueWaMsgsService(Resource):

    def post(self) -> dict:
        input = json.loads(request.data)
        input = QueueWaMsgsInput(**input)
        output = QueueWaMsgs(input).process()
        output = dataclasses.asdict(output)

        return output


class SendFCMMsgsService(Resource):

    def post(self) -> dict:
        input = json.loads(request.data)
        input = SendFCMMsgsInput(**input)
        output = SendFCMMsgs(input).process()
        output = dataclasses.asdict(output)

        return output


class BulkInsertUsersService(Resource):

    def post(self) -> dict:
        input = json.loads(request.data)
        input = BulkUploadInput(**input)
        output = BulkInsertUsers(input).process()
        output = dataclasses.asdict(output)

        return output
