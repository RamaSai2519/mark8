import json
import traceback
import threading
from pdf import Compute
from mark.helper import log
from quart_cors import cors
from flask_cors import CORS
from flask_restful import Api
from mark.model import Process
from starlette.routing import Mount
from server.services.controller import *
from starlette.applications import Starlette
from shared.models.interfaces import InvoiceData
from flask import Flask, request, jsonify, Response
from starlette.middleware.wsgi import WSGIMiddleware
from quart import Quart, jsonify as qjsonify, request as qrequest


flask_app = Flask(__name__)
quart_app = Quart(__name__)

CORS(flask_app)
quart_app = cors(quart_app)

api = Api(flask_app)
api.add_resource(BulkInsertUsersService, '/bulk_users')
api.add_resource(BulkScheduleService, '/bulk_schedule')
api.add_resource(QueueWaMsgsService, '/queue_wa_msgs')
api.add_resource(SendFCMMsgsService, '/send_fcm_msgs')
api.add_resource(ExcelUploadService, '/excel_upload')
api.add_resource(GatherDataService, '/gather_data')
api.add_resource(ChatService, '/chat')


@quart_app.route("/invoice", methods=["POST"])
async def generate_invoice() -> tuple:
    try:
        input_data = await qrequest.get_json()
        input = InvoiceData(**input_data)
        output = await Compute(input).compute()
        return qjsonify(output.__dict__), 200
    except Exception as e:
        traceback.print_exc()
        return qjsonify({"message": f"An error occurred: {str(e)}"}), 500


def process_call(callId: str) -> None:
    try:
        processor = Process(callId)
        success, message = processor.process()
        if not success:
            log(callId, message)
            return f"ERROR: {message}"
        return f"SUCCESS: {message}"
    except Exception as e:
        message = f"An error occurred processing call: {str(e)}"
        log(callId, message)
        log(callId, traceback.format_exc())
        return f"ERROR: {message}"


@flask_app.route("/process", methods=["POST"])
def process_call_route() -> tuple:
    input = json.loads(request.get_data())
    callId = input.get("callId", None)
    can_wait = input.get("canWait", False)
    if not callId:
        return jsonify({"message": "callId is required"}), 400
    if can_wait:
        message = process_call(callId)
        return jsonify({"message": message}), 200
    threading.Thread(target=process_call, args=(callId,)).start()
    return jsonify({"message": "Processing call"}), 200


@flask_app.after_request
def log_flask_response(response: Response) -> Response:
    message = 'path: ' + request.path + ' method: ' + \
        request.method + ' status: ' + str(response.status_code)
    print(message)
    return response


flask_asgi = WSGIMiddleware(flask_app.wsgi_app)

app = Starlette(routes=[
    Mount('/flask', app=flask_asgi),
    Mount('/quart', app=quart_app)
])

if __name__ == "__main__":
    import os
    import asyncio
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    ENV = os.environ.get('ENV')
    port = 8080
    if ENV != 'main':
        port = 8081

    config = Config()
    # config.bind = ["0.0.0.0:8080"]
    config.bind = [f"0.0.0.0:{port}"]
    asyncio.run(serve(app, config))
