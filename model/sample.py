from pymongo import MongoClient

import os
from dotenv import load_dotenv
load_dotenv()

def get_database():
    """ Method to get the cluster for Mongo """

    # Get URI and connect to cluster
    uri = os.getenv('MONGO_URI')
    cluster = MongoClient(uri)

    return cluster['mendel-tutor']


def create_collection(db, collection_name, validator):
    db.create_collection(collection_name, validator=validator)


# Plačiau apie validators: https://www.mongodb.com/docs/manual/reference/operator/query/jsonSchema/
student_scehma_validation = {
    '$jsonSchema': {
        'bsonType': 'object',                   # Visada su šitu prasideda
        'additionalProperties': True,           # Ar galima bus pridėti daugiau laukų, nei čia įrašyta
        'required': ['full_name', 'class'],     # Būtini
        'properties': {

            # Key value poros lauko ir jo reikalavimų
            # pvz. klasė turi būti int tarp 1 ir 12
            'class': {
                'bsonType': 'int',
                'minimum': 1,
                'maximum': 12,
                'description': "Student's specified class"
            }
        }
    }
}


if __name__ == "__main__":
    db = get_database()

    collection_name = "student"
    create_collection(db, "student", student_scehma_validation)

    print("Collections before dropping", db.list_collection_names())

    db[collection_name].drop()

    print("Collections after dropping", db.list_collection_names())

