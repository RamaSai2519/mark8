from config.constants import *
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
embeddings_collection = db["embeddings"]
fcm_tokens_collection = db["fcm_tokens"]
