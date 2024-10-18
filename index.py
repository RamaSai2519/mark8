from config import calls_collection
from helper import Helper

calls = list(calls_collection.find().limit(100))

apt_calls = []

for call in calls:
    duration = Helper.duration_str_to_seconds(call.get("duration", ""))
    if duration > 120 and duration < 180:
        apt_calls.append(call)

apt_calls.sort(key=lambda x: x.get("duration", 0), reverse=True)

for call in apt_calls:
    print(call.get("duration", 0), call.get("callId", ""))