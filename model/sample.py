from pymongo import MongoClient

import os
from dotenv import load_dotenv

from datetime import datetime
from dateutil.relativedelta import relativedelta

load_dotenv()

def get_database():
    """ Method to get the cluster for Mongo """

    # Get URI and connect to cluster
    uri = os.getenv('MONGO_URI')
    cluster = MongoClient(uri)

    return cluster['mendel-tutor']

def drop_selected_collections(db):
    collections_to_drop = ["student", "tutor", "lesson", "reviews"]
    for name in collections_to_drop:
        if name in db.list_collection_names():
            db[name].drop()
            print(f"Kolekcija '{name}' pašalinta.")
        else:
            print(f"Kolekcijos '{name}' nėra - praleidžiama.")


def create_collection(db, collection_name, validator):
    db.create_collection(collection_name, validator=validator)



# Plačiau apie validators: https://www.mongodb.com/docs/manual/reference/operator/query/jsonSchema/
student_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',                   # Visada su šitu prasideda
        'additionalProperties': True,           # Ar galima bus pridėti daugiau laukų, nei čia įrašyta
        'required': ['full_name','dob','subjects', 'class', 'parents_phone_number'],     # Būtini
        'properties': {
            'full_name': {
                'bsonType': 'string',
                'description': "Student's full name"
            },
            'dob':{
                'bsonType': 'date',
                'description': "Student's date of birth"
            },
            'class': {
                'bsonType': 'int',
                'minimum': 1,
                'maximum': 12,
                'description': "Student's specified class"
            },
            'subjects': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'string'
                },
                'description': "List of subjects the student takes"
            },
            'phone_number': {
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',  
                'description': "Student's phone number"
            },
            'parents_phone_number':{
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',  
                'description': "Parent's phone number"
            },
            'student_email': {
                'bsonType': 'string',
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Student's email"
            },
            'parents_email': {
                'bsonType': 'string',
                'pattern': r'^[^@]+@[^@]+\.[^@]+$',
                'description': "Parent's email"
            }

        }
    }
}

tutor_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',                   # Visada su šitu prasideda
        'additionalProperties': True,           # Ar galima bus pridėti daugiau laukų, nei čia įrašyta
        'required': ['full_name','dob','number_of_lessons','username','password_encrypted', 'email'],     # Būtini
        'properties': {
            'full_name': {
                'bsonType': 'string',
                'description': "Tutor's full name"
            },
            'dob':{
                'bsonType': 'date',
                'description': "Tutor's date of birth"
            },
            'rating': {
                'bsonType': 'double',
                'minimum': 0,
                'maximum': 5,
                'description': "Tutor's rating"
            },
            'number_of_lessons': {
                'bsonType': 'int',
                'minimum': 0,
                'description': "Tutor's specified class"
            },
            'subjects_students': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'required': ['student', 'subject'],
                    'properties': {
                        'student': {
                            'bsonType': 'objectId',
                            'description': "Reference to the student"
                        },
                        'subject':{
                            'bsonType': 'string',
                            'description': 'Subject that the student will be taught'
                        }
                    }
                },
                'description': "List of subjects the student takes"
            },
            'phone_number': {
                'bsonType': 'string',
                'pattern': r'^\+?\d{7,15}$',  
                'description': "Phone number"
            },
            'username':{
                'bsonType': 'string', 
                'description': "Username"
            },
            'password_encrypted':{
                'bsonType': 'string', 
                'description': "Username"
            },
            'email': {
            'bsonType': 'string',
            'pattern': r'^[^@]+@[^@]+\.[^@]+$',
            'description': "Tutor's email"
            }
        }
    }
}

lesson_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['time','tutor','students','subject','class','link'],
        'properties': {
            'time': {
            'bsonType': 'date',
            'description': "Lesson date and time"
            },
            'tutor': {
            'bsonType': 'objectId',
            'description': "Reference to the tutor"
            },
            'students': {
                'bsonType': 'array',
                'items': {
                    'bsonType': 'object',
                    'required': ['student','price','paid','moved'],
                    'properties': {
                        'student': {
                        'bsonType' : 'objectId',
                        'description': "Reference to the student"
                        },
                        'price' :{
                        'bsonType': 'double',
                        'minimum': 0,
                        'maximum': 150,
                        'description': 'Price of the lesson for the student'
                        },
                        'paid':{
                        'bsonType': "bool",
                        'description': "Whether the lesson is paid"
                        },
                        'moved':{
                        'bsonType': "bool",
                        'description': "Whether the lesson is moved"
                        }
                    }
                },
                'description': "List of students attending the lesson"
            },
            'subject': {
            'bsonType': 'string',
            'description': "Subject of the lesson"
            },
            'class': {
            'bsonType': 'int',
            'minimum': 1,
            'maximum': 12,
            'description': "Students specified class"
            },
            'type': {
            'bsonType': 'string',
            'description': "Type of the lesson"
            },
            'link': {
            'bsonType': 'string',
            'description': "Link for the lesson"
            }
        }
    }
}

reviews_schema_validation = {
    '$jsonSchema': {
        'bsonType': 'object',
        'additionalProperties': True,
        'required': ['time','tutor','student', 'ratings', 'type'],
        'properties': {
            'time': {
                'bsonType': 'date',
                'description': "Review date"
            },
            'tutor': {
                'bsonType': 'objectId',
                'description': "Reference to the tutor"
            },
            'student': {
                'bsonType': 'objectId',
                'description': "Reference to the student"
            },
            'ratings': {
                'bsonType': 'int',
                'minimum': 1,
                'maximum': 5,
                'description': "Rating from 1 to 5"
            },
            'for_tutor': {
                'bsonType': 'bool',
                'description': "Type of review (for tutor/parents)"
            }
        }
    }
}

if __name__ == "__main__":
    db = get_database()

    collections = {
        "student": student_schema_validation,
        "tutor": tutor_schema_validation,
        "lesson": lesson_schema_validation,
        "reviews": reviews_schema_validation
    }

    #Pereinam per visas kolekcijas ir sukuriam jas
    for name, schema in collections.items():
        create_collection(db, name, schema)


    print("Collections before dropping", db.list_collection_names())

    drop_selected_collections(db)

    print("Collections after dropping", db.list_collection_names())

