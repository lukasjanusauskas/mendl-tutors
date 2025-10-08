from bson import ObjectId

TUTOR_PAY_PERCENTAGE = 75

def get_tutor_review_count(review_collection, tutor_id: str):
    aggregate_output_cursor = review_collection.aggregate([
        { 
            "$match": {
                "tutor.tutor_id": ObjectId('68e3cedf7249569216674679'),
                "$or": [ 
                    {"type": {"$exists": False}}, 
                    {"type": {"$ne": "REVOKED"}}
                ]},
        },
        {
            "$count": "num_doc"
        },
    ])

    return next( aggregate_output_cursor )


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

    return next( aggregate_output_cursor )


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

    return next( aggregate_output_cursor )


def number_of_lessons_month_tutor(lesson_collection, tutor_id: str):
    pass


def pay_month_tutor(lesson_collection, tutor_id: str):
    pass


def number_of_lessons_month_student(lesson_collection, tutor_id: str):
    pass


def pay_month_student(lesson_collection, tutor_id: str):
    pass


if __name__ == "__main__":
    from api.connection import get_db
    db = get_db()

    lesson_collection = db['lesson']
    student_collection = db['student']
    tutor_collection = db['tutor']
    review_collection = db['review']

    print(
        calculate_tutor_rating(review_collection, "68e3cedf7249569216674679")
    )