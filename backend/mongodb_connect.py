# mongodb_connect.py

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

# Load all variables from .env
load_dotenv()

# Fetch the URI from environment
uri = os.getenv("MONGO_URI")

# Initialize client
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)

# Define DB
db = client["TickDatabase"]
