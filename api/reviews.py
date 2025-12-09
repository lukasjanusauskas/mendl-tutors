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
        if field in review_info:
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


def get_single_review(
    review_collection,
    review_id: str
) -> dict:
    
    review = review_collection.find_one({'_id': ObjectId(review_id)})

    if not review:
        raise ValueError('Review not available')

    output = {}

    if review['for_tutor']:
        first_name = review['tutor']['first_name']
        last_name = review['student']['last_name']
    else:
        first_name = review['student']['first_name']
        last_name = review['student']['last_name']
        
    output['Atsiliepimo autorius'] = f"{first_name} {last_name}"

    output['Atsiliepimas'] = review['review_text']
    output['Atsiliepimo laikas'] = review['time'].date()

    if 'rating' in review:
        output['Įvertinimas'] = review['rating']

    return output


def parse_review(review_doc: dict, filter_revoked: bool) -> dict:
    output = {}

    if review_doc['for_tutor']:
        first_name = review_doc['student']['first_name']
        last_name = review_doc['student']['last_name']
    else:
        first_name = review_doc['tutor']['first_name']
        last_name = review_doc['tutor']['last_name']
        
    output['Atsiliepimo autorius'] = f"{first_name} {last_name}"
    output['Atsiliepimas'] = review_doc['review_text']
    if 'rating' in review_doc:
        output['Įvertinimas'] = review_doc['rating']
    output['Atsiliepimo laikas'] = review_doc['time'].date()

    if filter_revoked == False and 'type' in review_doc:
        output = output | {'type': review_doc['type']}

    return output


def list_reviews_tutor(
    review_collection,
    tutor_id: str,
    filter_revoked: bool = True
) -> tuple[list,list]:

    recieved_reviews = []
    written_reviews = []

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

        parsed_review = parse_review(review_doc, filter_revoked)

        if review_doc['for_tutor']:
            recieved_reviews.append( 
                (review_doc['_id'], parsed_review) )
        else:
            written_reviews.append(
                (review_doc['_id'], parsed_review) )

    return recieved_reviews, written_reviews


def list_reviews_student(
    review_collection,
    student_id: str,
    filter_revoked: bool = True
) -> tuple[list,list]:

    recieved_reviews = []
    written_reviews = []

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

        parsed_review = parse_review(review_doc, filter_revoked)

        if not review_doc['for_tutor']:
            recieved_reviews.append( 
                (review_doc['_id'], parsed_review) )
        else:
            written_reviews.append(
                (review_doc['_id'], parsed_review) )

    return recieved_reviews, written_reviews

def list_reviews_student_tutor(
    review_collection,
    student_id: str,
    tutor_id: str,
    filter_revoked: bool = True
) -> list:

    reviews = []

    query = {
        'for_tutor': True,
        'student.student_id': ObjectId(student_id),
        'tutor.tutor_id': ObjectId(tutor_id)
    }

    for review_doc in review_collection.find(query):
        if 'type' in review_doc:
            if review_doc['type'] == 'REVOKED' and filter_revoked:
                continue

        parsed_review = parse_review(review_doc, filter_revoked)
        reviews.append( (review_doc['_id'], parsed_review) )

    return reviews

def avg_rating_student_tutor(
    review_collection,
    student_id: str,
    tutor_id: str
) -> float:

    ratings = []

    query = {
        'for_tutor': True,
        'student.student_id': ObjectId(student_id),
        'tutor.tutor_id': ObjectId(tutor_id),
        'rating': { '$exists': True }
    }

    for review_doc in review_collection.find(query):
        if 'type' in review_doc:
            if review_doc['type'] == 'REVOKED':
                continue

        ratings.append( review_doc['rating'] )

    if len(ratings) == 0:
        return 0.0

    return sum(ratings) / len(ratings)