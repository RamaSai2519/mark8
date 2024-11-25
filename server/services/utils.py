import json
import dataclasses
from flask import request
from flask_restful import Resource
from shared.models.interfaces import ExcelUploadInput
from server.models.excel_upload.main import ExcelUpload


class ExcelUploadService(Resource):

    def post(self) -> dict:
        input = json.loads(request.get_data())
        input = ExcelUploadInput(**input)
        output = ExcelUpload(input).process()
        output = dataclasses.asdict(output)

        return output
