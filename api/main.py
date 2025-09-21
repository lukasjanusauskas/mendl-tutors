from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv
load_dotenv()

uri = os.getenv('MONGO_URI')

cluster = MongoClient(uri, server_api=ServerApi(
    version='1', strict=True, deprecation_errors=True))

db = cluster['mendel-tutor']

app = Flask(__name__)

@app.route('/', methods = ['GET', 'POST'])
def home():
    collection_names = db.list_collection_names()
    return jsonify({'collection_names': collection_names})


if __name__ == '__main__':

    app.run(host = '0.0.0.0', debug = True)

    db.close()
