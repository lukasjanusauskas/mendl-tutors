from utils import (
    serialize_doc,
    parse_date_of_birth
)
from connection import get_db
from pymongo.results import (
    InsertOneResult,
    UpdateResult,
    DeleteResult
)
import re
from bson import ObjectId
from datetime import timedelta
import hashlib

def create_new_student(
    student_collection,
    student_info: dict
) -> InsertOneResult:
    """
    Sukurti studenta ir issaugoti i duombaze.
    Grazina InsertOneResult su inserted_id ir acknowledged.
    Patikrina ar toks studentas jau egzistuoja (pagal first_name ir gimimo datą).
    """

    student: dict = {}

    # 1️⃣ Tikriname privalomus laukus
    required_arguments = [
        'first_name', 
        'last_name', 
        'date_of_birth', 
        'class', 
        'subjects', 
        'password',
        'parents_phone_numbers'
    ]
    for field in required_arguments:
        if field not in student_info:
            raise KeyError(f'Truksta {field}')
        student[field] = student_info[field]

    # 2️⃣ Tikriname papildomus laukus
    optional_arguments = ['phone_number', 'student_email', 'parents_email']
    for field in optional_arguments:
        if field in student_info:
            student[field] = student_info[field]

    # 3️⃣ Konvertuojame gimimo datą į datetime
    date_of_birth_date = parse_date_of_birth(student_info['date_of_birth'])
    student['date_of_birth'] = date_of_birth_date

    # 4️⃣ Tikriname subjects
    if not isinstance(student['subjects'], list) or len(student['subjects']) == 0:
        raise ValueError("subjects turi buti ne tuscias masyvas")

    # 5️⃣ Tikriname, ar toks studentas jau egzistuoja (first_name + date_of_birth + parents_phone_number)
    date_of_birth_start = date_of_birth_date
    date_of_birth_end = date_of_birth_start + timedelta(days=1)
    existing_student = student_collection.find_one({
        "first_name": student['first_name'],
        "date_of_birth": {"$gte": date_of_birth_start, "$lt": date_of_birth_end},
        "parents_phone_numbers": { "$in": student['parents_phone_numbers'] }
    })
    if existing_student:
        raise ValueError("Toks mokinys jau egzistuoja!")

    password_encoded = student['password'].encode('utf-8')
    hash_algo = hashlib.sha256()
    hash_algo.update(password_encoded)
    student['password_hashed'] = hash_algo.hexdigest()
    del student['password']

    # 6️⃣ Įrašome į DB
    return student_collection.insert_one(student)


def get_student_by_id(student_collection, student_id: str):
    """Randa vieną studentą pagal ObjectId."""
    student = student_collection.find_one({"_id": ObjectId(student_id)})
    return serialize_doc(student) if student else None

def get_all_students(student_collection):
    """Gražina visų studentų sąrašą."""
    students = student_collection.find()
    return [serialize_doc(s) for s in students]

def get_students_by_name(student_collection, first_name: str, last_name: str):
    """Ieško studentų pagal vardą arba pavardę (case-insensitive)."""
    regex_first = re.compile(first_name, re.IGNORECASE)
    regex_last = re.compile(last_name, re.IGNORECASE)

    students = student_collection.find({
        "first_name": {"$regex": regex_first},
        "last_name": {"$regex": regex_last}
    })

    return [serialize_doc(s) for s in students]


def delete_student(student_collection, tutor_collection, student_id: str) -> dict:
    """
    Ištrina studentą iš DB pagal _id.
    Taip pat pašalina studentą iš visų korepetitorių 'students_subjects'.
    """
    result: DeleteResult = student_collection.delete_one({"_id": ObjectId(student_id)})

    if result.deleted_count == 1:
        # ištrinam studentą iš visų tutor.students_subjects
        tutor_collection.update_many(
            {},
            {"$pull": {"students_subjects": {"student_id": student_id}}}
        )
        return {"deleted": True}
    else:
        return {"deleted": False}

if __name__ == "__main__":
    db = get_db()
    student_collection = db['student']