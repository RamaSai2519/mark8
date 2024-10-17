import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

user_document = None
expert_document = None

client = MongoClient(os.getenv("MONGO_KEY"))

MAIN_LAMBDA_URL = str(os.getenv("MAIN_LAMBDA_URL"))

db = client["test"]
calls_collection = db["calls"]
users_collection = db["users"]
experts_collection = db["experts"]
timings_collection = db["timings"]
errorlog_collection = db["errorlogs"]
callsmeta_collection = db["callsmeta"]
schedules_collection = db["schedules"]
fcm_tokens_collection = db["fcm_tokens"]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
OPEN_AI_VERSION = os.getenv("OPEN_AI_VERSION")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
