import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from pymongo import MongoClient

load_dotenv()

user_document = None
expert_document = None

client = MongoClient(os.getenv("MONGO_KEY"))

main_lambda_url = str(os.getenv("MAIN_LAMBDA_URL"))

db = client["test"]
calls_collection = db["calls"]
users_collection = db["users"]
experts_collection = db["experts"]
fcm_tokens_collection = db["fcm_tokens"]
errorlog_collection = db["errorlogs"]
timings_collection = db["timings"]
callsmeta_collection = db["callsmeta"]
schedules_collection = db["schedules"]

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

open_ai_client = AzureOpenAI(
    azure_endpoint="https://sukoon-chat.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview",
    api_key="13c72289e9704b4ca63f683df19a7afe",
    api_version="2023-03-15-preview"
)
