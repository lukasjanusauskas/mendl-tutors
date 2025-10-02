import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

def get_db():
    uri = os.getenv('MONGO_URI')

    cluster = MongoClient(
        uri,
        server_api=ServerApi(version='1', strict=True, deprecation_errors=True),
        tls=True
    )

    return cluster['mendel-tutor']
