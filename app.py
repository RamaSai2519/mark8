import json
import traceback
import threading
from helper import log
from pdf import Compute
from model import Process
from quart_cors import cors
from interfaces import InvoiceData
from quart import Quart, request, jsonify

app = Quart(__name__)
app = cors(app)


@app.route("/invoice", methods=["POST"])
async def generate_invoice() -> tuple:
    try:
        input_data = await request.get_json()
        input = InvoiceData(**input_data)
        output = await Compute(input).compute()
        return jsonify(output.dict()), 200
    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


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
async def process_call_route() -> tuple:
    print("Processing call")
    input = json.loads(await request.get_data())
    callId = input.get("callId", None)
    can_wait = input.get("canWait", False)
    if not callId:
        return jsonify({"message": "callId is required"}), 400
    if can_wait:
        message = await process_call(callId)
        return jsonify({"message": message}), 200
    threading.Thread(target=process_call, args=(callId,)).start()
    return jsonify({"message": "Processing call"}), 200


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    app.run(debug=True, port=8080)
