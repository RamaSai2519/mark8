from mark.config.constants import *
from pymongo import MongoClient

client = MongoClient(DB_URL)

db = client["test"]
calls_collection = db["calls"]
users_collection = db["users"]
experts_collection = db["experts"]
timings_collection = db["timings"]
errorlog_collection = db["errorlogs"]
callsmeta_collection = db["callsmeta"]
schedules_collection = db["schedules"]
fcm_tokens_collection = db["fcm_tokens"]

embeddings_db = client["embeddings"]
constants_collection = embeddings_db["constants"]
transcripts_collection = embeddings_db["transcripts"]
call_prompts_collection = embeddings_db["call_prompts"]
recommendations_collection = embeddings_db["recommendations"]
