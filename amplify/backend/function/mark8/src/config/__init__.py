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
embeddings_collection = db["embeddings"]
fcm_tokens_collection = db["fcm_tokens"]

GPT_API_KEY = os.getenv("GPT_API_KEY")
GPT_VERSION = os.getenv("GPT_VERSION")
ADA_API_KEY = os.getenv("ADA_API_KEY")
ADA_VERSION = os.getenv("ADA_VERSION")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AZURE_GPT_ENDPOINT = os.getenv('AZURE_GPT_ENDPOINT')
AZURE_ADA_ENDPOINT = os.getenv('AZURE_ADA_ENDPOINT')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
