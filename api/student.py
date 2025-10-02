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

def create_new_student(
    student_collection,
    student_info: dict
) -> InsertOneResult:
    """
    Sukurti studenta ir issaugoti i duombaze.
    Grazina InsertOneResult su inserted_id ir acknowledged.
    Patikrina ar toks studentas jau egzistuoja (pagal full_name ir gimimo datą).
    """

    student: dict = {}

    # 1️⃣ Tikriname privalomus laukus
    required_arguments = ['full_name', 'dob', 'class', 'subjects', 'parents_phone_number']
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
    dob_date = parse_date_of_birth(student_info['dob'])
    student['dob'] = dob_date

    # 4️⃣ Tikriname subjects
    if not isinstance(student['subjects'], list) or len(student['subjects']) == 0:
        raise ValueError("subjects turi buti ne tuscias masyvas")

    # 5️⃣ Tikriname, ar toks studentas jau egzistuoja (full_name + dob)
    dob_start = dob_date
    dob_end = dob_start + timedelta(days=1)
    existing_student = student_collection.find_one({
        "full_name": student['full_name'],
        "dob": {"$gte": dob_start, "$lt": dob_end}
    })
    if existing_student:
        raise ValueError("Studentas su tokiu vardu ir gimimo data jau egzistuoja!")

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

def get_students_by_name(student_collection, name: str):
    """Ieško studentų pagal vardą arba pavardę (case-insensitive)."""
    regex = re.compile(name, re.IGNORECASE)
    students = student_collection.find({"full_name": {"$regex": regex}})
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