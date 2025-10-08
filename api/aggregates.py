from bson import ObjectId

TUTOR_PAY_PERCENTAGE = 75

def get_tutor_review_count(review_collection, tutor_id: str):
    aggregate_output_cursor = review_collection.aggregate([
        { 
            "$match": {
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [ 
                    {"type": {"$exists": False}}, 
                    {"type": {"$ne": "REVOKED"}}
                ]},
        },
        {
            "$count": "num_doc"
        },
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['num_doc']
    except StopIteration:
        return None


def get_student_review_count(review_collection, student_id: str):
    aggregate_output_cursor = review_collection.aggregate([
        { 
            "$match": {
                "student.student_id": ObjectId(student_id),
                "$or": [ 
                    {"type": {"$exists": False}}, 
                    {"type": {"$ne": "REVOKED"}}
                ]}
        },
        {
            "$count": "num_doc"
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['num_doc']
    except StopIteration:
        return None


def calculate_tutor_rating(review_collection, tutor_id: str):
    aggregate_output_cursor = review_collection.aggregate([
        { 
            "$match": { 
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": { "$ne": "REVOKED" } }
                ], 
                "rating": { "$exists": True } 
            }
        },
        { 
            "$group": { 
                "_id": None,
                "average_rating": { "$avg": "$rating" }
            }
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['average_rating']
    except StopIteration:
        return None


def number_of_lessons_month_tutor(lesson_collection, tutor_id: str):
    aggregate_output_cursor = lesson_collection.aggregate([
        { 
            "$match": { 
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": "ACTIVE" }
                ]
            }
        },
        { 
            "$count": "num_doc"
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['num_doc']
    except StopIteration:
        return None


def pay_month_tutor(lesson_collection, tutor_id: str):
    aggregate_output_cursor = lesson_collection.aggregate([
        { 
            "$match": { 
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": "ACTIVE" }
                ]
            }
        },
        { "$unwind": "$students" },
        { 
            "$group": {
                "_id": None,
                "monthly_pay": {"$sum": "$students.price"}
            }
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['monthly_pay']
    except StopIteration:
        return None


def number_of_lessons_month_student(lesson_collection, student_id: str):
    aggregate_output_cursor = lesson_collection.aggregate([
        {
        "$match": {
            "$and": [
            { "students.student_id": ObjectId(student_id) },
            {
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": "ACTIVE" }
                ]
            }]}
        },
        { 
            "$count": "num_doc"
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['num_doc']
    except StopIteration:
        return None


def pay_month_student(lesson_collection, student_id: str):
    aggregate_output_cursor = lesson_collection.aggregate([
        { 
            "$match": { 
                "students.student_id": ObjectId(student_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": "ACTIVE" }
                ]
            }
        },
        { "$unwind": "$students" },
        { 
            "$group": {
                "_id": None,
                "monthly_pay": {"$sum": "$students.price"}
            }
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['monthly_pay']
    except StopIteration:
        return None


if __name__ == "__main__":
    from api.connection import get_db
    db = get_db()

    lesson_collection = db['lesson']
    student_collection = db['student']
    tutor_collection = db['tutor']
    review_collection = db['review']

    print(
        pay_month_tutor(lesson_collection, "68e015c72541f9f89f6ca611")
    )