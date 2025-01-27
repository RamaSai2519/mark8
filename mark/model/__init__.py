import pytz
import time
import traceback
from mark.helper import log
from bson import ObjectId
from mark.helper import Helper
from mark.compute import Compute
from datetime import datetime
from shared.db.users import get_user_collection
from shared.db.experts import get_experts_collections
from shared.models.interfaces import Call, User, Expert
from shared.db.calls import get_calls_collection, get_callsmeta_collection


class Process:
    def __init__(self, callId: str) -> None:
        self.callId = callId
        self.users_collection = get_user_collection()
        self.calls_collection = get_calls_collection()
        self.experts_collection = get_experts_collections()
        self.callsmeta_collection = get_callsmeta_collection()

    def get_user(self, user_id: ObjectId) -> None | User:
        user = self.users_collection.find_one({"_id": user_id})
        if not user:
            return None
        user = Helper.clean_dict(user, User)
        return User(**user)

    def get_expert(self, expert_id: ObjectId) -> None | Expert:
        expert = self.experts_collection.find_one({"_id": expert_id})
        if not expert:
            return None
        expert = Helper.clean_dict(expert, Expert)
        return Expert(**expert)

    def get_call(self) -> None | Call:
        call = self.calls_collection.find_one({"callId": self.callId})
        if not call:
            return None
        call = Helper.clean_dict(call, Call)
        return Call(**call)

    def get_user_calls_count(self, user_id: ObjectId) -> int:
        return self.calls_collection.count_documents({"user": user_id})

    def update_user(self, user_id: ObjectId, customer_persona: dict) -> None:
        update_query = {"_id": user_id}
        update_values = {"$set": {"customerPersona": customer_persona}}
        self.users_collection.update_one(update_query, update_values)

    def update_expert(self, expert_id: ObjectId, expert_persona: dict) -> None:
        update_query = {"_id": expert_id}
        update_values = {"$set": {"persona": expert_persona}}
        self.experts_collection.update_one(update_query, update_values)

    def update_call(self, call_id: str, conversation_score: float) -> None:
        update_query = {"callId": call_id}
        update_values = {"$set": {"conversationScore": conversation_score}}
        self.calls_collection.update_one(update_query, update_values)

    def update_call_meta(self, call_id: str, update_values: dict) -> None:
        if self.callsmeta_collection.find_one({"callId": call_id}):
            self.callsmeta_collection.update_one(
                {"callId": call_id},
                {"$set": update_values},
            )
        else:
            update_values["createdAt"] = datetime.now(pytz.utc)
            self.callsmeta_collection.insert_one(
                update_values,
            )

    def validate_call(self, call: Call) -> bool:
        if not call or call.status != "successful":
            return False, f"Call {self.callId} not found or not successful"
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
            log(self.callId, traceback.format_exc())
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
            "conversationScore": output.score,
            "updatedAt": datetime.now(pytz.utc),
            "scoreBreakup": output.score_details,
            "userCallback": output.user_callback,
            "sarathiFeedback": output.saarthi_feedback,
        }

        self.update_call(call.callId, output.score)
        self.update_call_meta(call.callId, meta_update)
        self.update_user(user._id, output.customer_persona)
        self.update_expert(expert._id, output.expert_persona)
        Helper.updater(call.callId, str(expert._id),
                       expert.phoneNumber, str(user._id))
        Helper.update_user_interest(
            call.callId, output.user_interest, str(user._id))

        finish = time.perf_counter()
        total_seconds = round(finish - start, 2)
        return True, f"Call {self.callId} processed successfully in {total_seconds} seconds"
