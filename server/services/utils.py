import json
import dataclasses
from flask import request
from flask_restful import Resource
from server.models.excel_upload.main import ExcelUpload
from server.models.bulk_schedule.main import BulkSchedule
from shared.models.interfaces import ExcelUploadInput, BulkScheduleInput


class ExcelUploadService(Resource):

    def post(self) -> dict:
        input = json.loads(request.get_data())
        input = ExcelUploadInput(**input)
        output = ExcelUpload(input).process()
        output = dataclasses.asdict(output)

        return output


class BulkScheduleService(Resource):

    def post(self) -> dict:
        input = json.loads(request.get_data())
        input = BulkScheduleInput(**input)
        output = BulkSchedule(input).process()
        output = dataclasses.asdict(output)

        return output
