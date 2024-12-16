from shared.models.interfaces import Call
from mark.config import calls_collection
from mark.helper import Helper
from mark.model import Process
from datetime import datetime
from pprint import pprint
import requests
import time
import pytz

while True:
    calls = list(calls_collection.find().sort("initiatedTime", -1))

    apt_calls: list[Call] = []

    for call in calls:
        Processor = Process(call["callId"])
        call_doc = Helper.clean_dict(call, Call)
        call = Call(**call_doc)
        valid, message = Processor.validate_call(call)
        if valid:
            if call.conversationScore or call.conversationScore == 0:
                continue
            apt_calls.append(call)

    pprint(apt_calls)
    print(f"Processing {len(apt_calls)} calls")
    for call in apt_calls:
        payload = {"callId": call.callId, "canWait": True}
        print(f"Requesting processing for: {call.callId}")
        response = requests.post(
            "http://localhost:8080/flask/process", json=payload)
        try:
            print(response.json())
        except requests.exceptions.JSONDecodeError:
            print("Failed to decode JSON response")

    # Sleep till 10 PM
    ist = pytz.timezone('Asia/Kolkata')
    desired_time = datetime.now(ist).replace(
        hour=22, minute=0, second=0, microsecond=0)
    current_time = datetime.now(ist)
    if current_time > desired_time:
        time.sleep(86400 - (current_time - desired_time).total_seconds())
    else:
        time.sleep((desired_time - current_time).total_seconds())
