import json
import awsgi
import traceback
from helper import log
from model import Process
from flask_cors import CORS
from flask import Flask, request, jsonify

app = Flask(__name__)
CORS(app)


def process_call(callId: str) -> None:
    try:
        processor = Process(callId)
        success, message = processor.process()
        if not success:
            log(message)
            return jsonify({"message": message}), 400
        return jsonify({"message": message}), 200
    except Exception as e:
        message = f"An error occurred processing call {callId}: {str(e)}"
        log(message)
        log(message)
        log(traceback.format_exc())
        return jsonify({"message": message}), 500


@app.route("/process", methods=["POST"])
def process_call_route():
    input = json.loads(request.get_data())
    callId = input.get("callId", None)
    if not callId:
        return jsonify({"message": "callId is required"}), 400

    return process_call(callId)


def handler(event, context):
    log(event)
    return awsgi.response(app, event, context)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
