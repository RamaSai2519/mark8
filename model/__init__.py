import pytz
from config import *
from bson import ObjectId
from helper import Helper
from compute import Compute
from datetime import datetime
from interfaces import Call, User, Expert


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
            return False
        if call.conversationScore:
            return False
        if call.recording_url in ["None", "", None]:
            return False
        duration = Helper.duration_str_to_seconds(call.duration)
        if duration > 120:
            return False
        return True

    def process(self) -> bool:
        call = self.get_call()
        if not call:
            return False
        call_document = call.__dict__
        if not self.validate_call(call):
            return False

        user = self.get_user(call.user)
        expert = self.get_expert(call.expert)
        if not user or not expert:
            return False
        user_name = user.name or user.phoneNumber
        expert_name = expert.name or expert.phoneNumber

        user_calls = self.get_user_calls_count(call.user)

        computer = Compute(call_document, user_name,
                           expert_name, user.customerPersona, user_calls)
        output = computer.process_call()

        if not output or not output.transcript:
            return False

        transcript_url = Helper.upload_transcript(output.transcript, call.callId)
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
        self.update_call(call.callId, output.conversation_score)
        Helper.updater(str(expert._id), expert.phoneNumber)

        return True
