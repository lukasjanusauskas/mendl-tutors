from pymongo import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv
import traceback
load_dotenv()

# Replace the placeholder with your Atlas connection string
uri = os.getenv('MONGO_URI')

# Create a MongoClient with a MongoClientOptions object to set the Stable API version
cluster = MongoClient(uri, server_api=ServerApi(
    version='1', strict=True, deprecation_errors=True))

# Connect the client to the server (optional starting in v4.7)
try:
    db = cluster['mendel-tutor']
    collection = db['tutors']

    tutors = [
        {'_id': 1, 'firstname': 'tadas', 'lastname': 'jonaitis', 'subjects': ['LIT', 'MAT', 'ANG']},
    ]

    print(collection)

    cluster.close()

except:
    print('Error', traceback.format_exc(), sep='\n')