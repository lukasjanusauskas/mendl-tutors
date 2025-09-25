from flask import Flask, jsonify, request
from connection import get_db

db = get_db()
app = Flask(__name__)

@app.route('/', methods = ['GET', 'POST'])
def home():
    collection_names = db.list_collection_names()
    return jsonify({'collection_names': collection_names})


if __name__ == '__main__':

    app.run(host = '0.0.0.0', debug = True)

    db.close()
