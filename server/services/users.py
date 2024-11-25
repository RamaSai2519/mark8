import json
import dataclasses
from flask import request
from flask_restful import Resource
from shared.models.interfaces import GatherDataInput
from server.models.gather_data.main import GatherData


class GatherDataService(Resource):

    def get(self) -> dict:
        input_params = request.args
        input = GatherDataInput(**input_params)
        output = GatherData(input).process()
        output = dataclasses.asdict(output)

        return output
