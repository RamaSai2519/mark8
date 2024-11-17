import json
import traceback
import threading
from helper import log
from model import Process
from flask_cors import CORS
from pdf import InvoiceService
from flask import Flask, request, jsonify
from flask_restful import Api

app = Flask(__name__)
CORS(app)
api = Api(app)

api.add_resource(InvoiceService, "/invoice")


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


@app.route("/process", methods=["POST"])
def process_call_route() -> tuple:
    print("Processing call")
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


if __name__ == "__main__":
    app.run(debug=True, port=8080)
