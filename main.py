from pymongo import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv
import traceback
load_dotenv()

# Get URI from .env file
uri = os.getenv('MONGO_URI')

# Create a MongoClient to connect with cluster
cluster = MongoClient(uri, server_api=ServerApi(
    version='1', strict=True, deprecation_errors=True))

try:
    # Get database from client
    db = cluster['mendel-tutor']
    # Get connection from datbase
    collection = db['tutors']

finally:
    cluster.close()
