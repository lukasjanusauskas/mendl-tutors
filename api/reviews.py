from pymongo.results import InsertOneResult
from bson import ObjectId
from api.utils import serialize_doc
from datetime import timedelta, datetime


def create_review(
    review_collection,
    tutor_collection,
    student_collection,
    review_info: dict
) -> InsertOneResult:
    review = {}

    # Pasiimame optional ir required argumentus
    required_arguments = ['tutor_id', 'student_id', 'for_tutor', 'review_text']
    for field in required_arguments:
        if field not in review_info:
            raise KeyError(f'Truksta {field}')
        review[field] = review_info[field]

    review['time'] = datetime.now()

    optional_arguments = ['rating']
    for field in optional_arguments:
        if field in review:
            review[field] = review_info[field]

    # Patikrinti, ar tutor egiztuoja
    tutor = tutor_collection.find_one({'_id': ObjectId( review_info['tutor_id'] )})
    if not tutor:
        raise ValueError('Tokio korepetitoriaus nera')

    # Patikrinti, ar tutor turi toki mokini
    student_ids_tutor = [ stud_sub_dict['student']['student_id']
        for stud_sub_dict in tutor['students_subjects']]

    print(student_ids_tutor)

    if not review['student_id'] in student_ids_tutor:
        raise ValueError('Mokinys nepriklauso mkoytojui')

    # "Ispakuoti" korepetitoriaus ir mokinio reiksmes
    review['tutor'] = {
        'tutor_id': tutor['_id'],
        'first_name': tutor['first_name'],
        'last_name': tutor['last_name']
    }

    student = student_collection.find_one({'_id': ObjectId( review['student_id'] )})
    review['student'] = {
        'student_id': student['_id'],
        'first_name': student['first_name'],
        'last_name': student['last_name']
    }

    del review['tutor_id']
    del review['student_id']

    # Prideti prie duomenu bazes
    return review_collection.insert_one(review)


def revoke_review(
    review_collection,
    review_id: str
) -> dict:

    if not review_collection.find_one({'_id': ObjectId(review_id)}):
        raise ValueError('Tokio review nera')

    return review_collection.find_one_and_update(
        {'_id': ObjectId( review_id )},
        {'$set': {'type': 'REVOKED'}}
    )


def list_reviews_tutor(
    review_collection,
    tutor_id: str,
    filter_revoked: bool = True
):
    list_reviews = []
    year = datetime.now().year
    month = datetime.now().month

    query = {
        'tutor.tutor_id': ObjectId(tutor_id),
        "time": { "$gte": datetime(year, month, 1) },
        "time": { "$lt": datetime(year, month+1, 1) }
    }

    for review_doc in review_collection.find(query):
        if 'type' in review_doc:
            if review_doc['type'] == 'REVOKED' and filter_revoked:
                continue

        if not review_doc['for_tutor']:
            continue

        review_doc = {
            '_id': str(review_doc['_id']),
            'tutor_first_name': review_doc['tutor']['first_name'],
            'tutor_last_name': review_doc['tutor']['last_name'],
            'student_first_name': review_doc['student']['first_name'],
            'student_last_name': review_doc['student']['last_name'],
            'review_text': review_doc['review_text']
        }

        if 'rating' in review_doc:
            review_doc = review_doc | {'rating': review_doc['rating']}

        if filter_revoked == False and 'type' in review_doc:
            review_doc = review_doc | {'type': review_doc['type']}

        list_reviews.append( review_doc )

    return list_reviews


def list_reviews_student(
    review_collection,
    student_id: str,
    year: int | None = None,
    month: int | None = None,
    filter_revoked: bool = True
):
    list_reviews = []
    year = datetime.now().year
    month = datetime.now().month

    query = {
        'student.student_id': ObjectId(student_id),
        "time": { "$gte": datetime(year, month, 1) },
        "time": { "$lt": datetime(year, month+1, 1) }
    }
    for review_doc in review_collection.find(query):
        if 'type' in review_doc:
            if review_doc['type'] == 'REVOKED' and filter_revoked:
                continue

        if review_doc['for_tutor']:
            continue

        review_doc = {
            '_id': str(review_doc['_id']),
            'tutor_first_name': review_doc['tutor']['first_name'],
            'tutor_last_name': review_doc['tutor']['last_name'],
            'student_first_name': review_doc['student']['first_name'],
            'student_last_name': review_doc['student']['last_name'],
            'review_text': review_doc['review_text']
        }

        if 'rating' in review_doc:
            review_doc = review_doc | {'rating': review_doc['rating']}

        if filter_revoked == False and 'type' in review_doc:
            review_doc = review_doc | {'type': review_doc['type']}

        list_reviews.append( review_doc )

    return list_reviews