import pytz
import time
from bson import ObjectId
from helper import Helper
from compute import Compute
from datetime import datetime
from interfaces import Call, User, Expert
from config import calls_collection, callsmeta_collection, experts_collection, users_collection


class Process:
    def __init__(self, callId: str) -> None:
        self.callId = callId

    def get_user(self, user_id: ObjectId) -> None | User:
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return None
        user = Helper.clean_dict(user, User)
        return User(**user)

    def get_expert(self, expert_id: ObjectId) -> None | Expert:
        expert = experts_collection.find_one({"_id": expert_id})
        if not expert:
            return None
        expert = Helper.clean_dict(expert, Expert)
        return Expert(**expert)

    def get_call(self) -> None | Call:
        call = calls_collection.find_one({"callId": self.callId})
        if not call:
            return None
        call = Helper.clean_dict(call, Call)
        return Call(**call)

    def get_user_calls_count(self, user_id: ObjectId) -> int:
        return calls_collection.count_documents({"user": user_id})

    def update_user(self, user_id: ObjectId, customer_persona: dict) -> None:
        update_query = {"_id": user_id}
        update_values = {"$set": {"customerPersona": customer_persona}}
        users_collection.update_one(update_query, update_values)

    def update_expert(self, expert_id: ObjectId, expert_persona: dict) -> None:
        update_query = {"_id": expert_id}
        update_values = {"$set": {"persona": expert_persona}}
        experts_collection.update_one(update_query, update_values)

    def update_call(self, call_id: str, conversation_score: float) -> None:
        update_query = {"callId": call_id}
        update_values = {"$set": {"conversationScore": conversation_score}}
        calls_collection.update_one(update_query, update_values)

    def update_call_meta(self, call_id: str, update_values: dict) -> None:
        if callsmeta_collection.find_one({"callId": call_id}):
            callsmeta_collection.update_one(
                {"callId": call_id},
                {"$set": update_values},
            )
        else:
            update_values["createdAt"] = datetime.now(pytz.utc)
            callsmeta_collection.insert_one(
                update_values,
            )

    def validate_call(self, call: Call) -> bool:
        if not call or call.status != "successful":
            return False, f"Call {self.callId} not found or not successful"
        if call.conversationScore or call.conversationScore == 0:
            return False, f"Call {self.callId} already processed"
        if call.recording_url in ["None", "", None]:
            return False, f"Call {self.callId} has no recording"
        duration = Helper.duration_str_to_seconds(call.duration)
        if duration < 120:
            return False, f"Call {self.callId} duration is less than 2 minutes"
        return True, ""

    def process(self) -> tuple[bool, str]:
        start = time.perf_counter()
        call = self.get_call()
        if not call:
            return False, f"Call {self.callId} not found"
        valid, message = self.validate_call(call)
        if not valid:
            return False, message

        user = self.get_user(call.user)
        expert = self.get_expert(call.expert)
        if not user or not expert:
            return False, f"User or expert not found for call {self.callId}"
        user_name = user.name or user.phoneNumber
        expert_name = expert.name or expert.phoneNumber

        user_calls = self.get_user_calls_count(call.user)

        call_document = call.__dict__
        computer = Compute(call_document, user_name,
                           expert_name, user.customerPersona, user_calls, expert.persona)
        try:
            output = computer.process_call()
        except Exception as e:
            if str(e) == "Inappropriate content found":
                self.update_call(call.callId, 0)
                return False, f"Inappropriate content found for call {self.callId}"
            return False, f"An error occurred processing call {self.callId}: {str(e)}"

        if not output or not output.transcript:
            return False, f"Transcript not completed for call {self.callId}"

        transcript_url = Helper.get_transcript_url(self.callId)
        meta_update = {
            "user": user._id,
            "callId": call.callId,
            "Topics": output.topics,
            "expert": str(expert._id),
            "Summary": output.summary,
            "transcript_url": transcript_url,
            "updatedAt": datetime.now(pytz.utc),
            "userCallback": output.user_callback,
            "sarathiFeedback": output.saarthi_feedback,
            "conversationScore": output.conversation_score,
            "scoreBreakup": output.conversation_score_details
        }

        self.update_call_meta(call.callId, meta_update)
        self.update_user(user._id, output.customer_persona)
        self.update_expert(expert._id, output.expert_persona)
        self.update_call(call.callId, output.conversation_score)
        Helper.updater(str(expert._id), expert.phoneNumber)

        finish = time.perf_counter()
        total_seconds = round(finish - start, 2)
        return True, f"Call {self.callId} processed successfully in {total_seconds} seconds"
