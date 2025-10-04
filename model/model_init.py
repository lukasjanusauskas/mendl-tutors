from pymongo import MongoClient

import os
from dotenv import load_dotenv
from validators import (
    student_schema_validation, 
    tutor_schema_validation, 
    lesson_schema_validation, 
    review_schema_validation
)

from datetime import datetime
from dateutil.relativedelta import relativedelta

load_dotenv()

def get_database():
    """ Method to get the cluster for Mongo """

    # Get URI and connect to cluster
    uri = os.getenv('MONGO_URI')
    cluster = MongoClient(uri)

    return cluster['mendel-tutor']

def drop_selected_collections(db, collections_to_drop: list[str]):
    for name in collections_to_drop:
        if name in db.list_collection_names():
            db[name].drop()
            print(f"Kolekcija '{name}' pašalinta.")
        else:
            print(f"Kolekcijos '{name}' nėra - praleidžiama.")


def create_collection(db, collection_name: str, validator: dict):
    db.create_collection(collection_name, validator=validator)


if __name__ == "__main__":
    db = get_database()

    collections = {
        "student": student_schema_validation,
        "tutor": tutor_schema_validation,
        "lesson": lesson_schema_validation,
        "review": review_schema_validation
    }

    collections_to_drop = ['review']
    drop_selected_collections(db, collections_to_drop)
    print("Collections after deletion", db.list_collection_names())

    #Pereinam per visas kolekcijas ir sukuriam jas
    for name, schema in collections.items():
        if name in db.list_collection_names():
            continue
        create_collection(db, name, schema)

    print("Collections after instantiation", db.list_collection_names())

    # print("Collections after dropping", db.list_collection_names())

