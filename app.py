import json
import awsgi
import traceback
from model import Process
from flask_cors import CORS
from helper.notify import notify
from flask import Flask, request

app = Flask(__name__)
CORS(app)


def process_call(callId: str) -> None:
    try:
        processor = Process(callId)
        output = processor.process()
        if not output:
            raise Exception("Processing failed")

        return "Call processed successfully", 200
    except Exception as e:
        message = f"An error occurred processing call {callId}: {str(e)}"
        notify(message)
        print(message)
        print(traceback.format_exc())
        return "An error occurred", 500


@app.route("/process", methods=["POST"])
def process_call_route() -> tuple:
    input = json.loads(request.get_data())
    callId = input.get("callId", None)
    if not callId:
        return "Call ID not provided", 400

    return process_call(callId)


def handler(event, context):
    print(event)
    return awsgi.response(app, event, context)


if __name__ == "__main__":
    app.run(debug=True, port=8080)
