"""
Tutor can be:
- added
- assign/remove students
- add or update phone/email
- update fields (email)
"""

from utils import (
    serialize_doc,
    parse_date_of_birth
)
import hashlib
from pymongo.results import (
    InsertOneResult,
    UpdateResult,
    DeleteResult
)

from connection import get_db
import re
from bson import ObjectId
from datetime import datetime, timedelta


def create_new_tutor(tutor_collection, tutor_info: dict) -> InsertOneResult:
    """
    Sukurti korepetitoriu ir įrašyti į duombazę.
    Grazina InsertOneResult su inserted_id ir acknowledged.
    Patikrina ar toks korepetitorius jau egzistuoja (pagal full_name ir gimimo datą).
    """

    tutor: dict = {}

    # 1️⃣ Tikriname privalomus laukus
    required_arguments = ['full_name', 'dob', 'email', 'password', 'subjects']
    for field in required_arguments:
        if field not in tutor_info:
            raise KeyError(f'Truksta {field}')
        tutor[field] = tutor_info[field]

    # 2️⃣ Tikriname papildomus laukus
    optional_parameters = ['phone_number']
    for field in optional_parameters:
        if field in tutor_info:
            tutor[field] = tutor_info[field]

    # 3️⃣ Konvertuojame gimimo datą į datetime objektą
    dob_date = parse_date_of_birth(tutor_info['dob'])
    tutor['dob'] = dob_date

    # 4️⃣ Patikriname, ar toks tutor jau egzistuoja (full_name + dob)
    dob_start = dob_date
    dob_end = dob_start + timedelta(days=1)
    existing_tutor = tutor_collection.find_one({
        "full_name": tutor['full_name'],
        "dob": {"$gte": dob_start, "$lt": dob_end}
    })
    if existing_tutor:
        raise ValueError("Korepetitorius su tokiu vardu ir gimimo data jau egzistuoja!")

    # 5️⃣ Patikriname unikalų e-mail
    if tutor_collection.find_one({"email": tutor['email']}) is not None:
        raise ValueError('Email turi buti unikalus')

    # 6️⃣ Patikriname subjects
    if not isinstance(tutor['subjects'], list) or len(tutor['subjects']) == 0:
        raise ValueError("subjects turi buti ne tuscias masyvas su objektais")

    # 7️⃣ Hashinti slaptažodį
    password_encoded = tutor['password'].encode('utf-8')
    hash_algo = hashlib.sha256()
    hash_algo.update(password_encoded)
    tutor['password_encrypted'] = hash_algo.hexdigest()
    del tutor['password']

    # 8️⃣ Papildomi laukai
    tutor['students_subjects'] = []
    tutor['number_of_lessons'] = 0

    # 9️⃣ Įrašome į DB
    return tutor_collection.insert_one(tutor)


def assign_student_to_tutor(
    tutor_collection,
    student_collection,
    tutor_email: str,
    student_id: str,
    subject: str
) -> UpdateResult:
    """
    Priskirti studenta prie korepetitoriaus pagal email ir subject.
    Grazina UpdateResult su informacija apie update.
    """

    # 1️⃣ Paimti studenta is DB
    student = student_collection.find_one({"_id": ObjectId(student_id)})
    if not student:
        raise ValueError("Studentas su tokiu ID nerastas")

    # 2️⃣ Patikrinti ar egzistuoja korepetitorius pagal email
    tutor = tutor_collection.find_one({"email": tutor_email})
    if not tutor:
        raise ValueError("Korepetitorius su tokiu email nerastas")

    # 3️⃣ Patikrinti ar korepetitorius moko tokio subject
    tutor_subjects = [s.get("subject") for s in tutor.get("subjects", [])]
    if subject not in tutor_subjects:
        raise ValueError("Korepetitorius nemoko sio dalyko")

    # 4️⃣ Patikrinti ar studentas jau priskirtas prie sio subject
    already_assigned = any(
        s.get("student_id") == str(student["_id"]) and s.get("subject") == subject
        for s in tutor.get("students_subjects", [])
    )
    if already_assigned:
        raise ValueError("Studentas jau priskirtas prie sio dalyko")

    # 5️⃣ Sukurti įrašą studentui
    student_entry = {
        "student_id": str(student["_id"]),
        "full_name": student["full_name"],
        "subject": subject
    }

    # 6️⃣ Pridėti prie tutor.students_subjects
    update_result = tutor_collection.update_one(
        {"email": tutor_email},
        {
            "$push": {"students_subjects": student_entry},
            "$inc": {"number_of_lessons": 0}  # paliekam lauką valdomą ateityje
        }
    )

    return update_result

def get_tutor_students(
    tutor_collection,
    student_collection,
    tutor_email: str
) -> list[dict]:
    """
    Grazina visus tutor studentus su vardais ir subjectais.
    """

    tutor = tutor_collection.find_one({"email": tutor_email})
    if not tutor:
        raise ValueError("Korepetitorius nerastas")

    students_subjects = tutor.get("students_subjects", [])
    results = []

    for entry in students_subjects:
        student = student_collection.find_one({"_id": ObjectId(entry["student_id"])})
        if student:
            results.append({
                "student_id": entry["student_id"],
                "full_name": student.get("full_name", "Nezinomas"),
                "subject": entry["subject"]
            })

    return results

def get_tutor_by_id(tutor_collection, tutor_id: str):
    """Randa vieną korepetitorių pagal ObjectId."""
    tutor = tutor_collection.find_one({"_id": ObjectId(tutor_id)})
    return serialize_doc(tutor) if tutor else None

def get_all_tutors(tutor_collection):
    """Gražina visų korepetitorių sąrašą."""
    tutors = tutor_collection.find()
    return [serialize_doc(t) for t in tutors]

def get_tutors_by_name(tutor_collection, name: str):
    """Ieško korepetitorių pagal vardą arba pavardę (case-insensitive)."""
    regex = re.compile(name, re.IGNORECASE)
    tutors = tutor_collection.find({"full_name": {"$regex": regex}})
    return [serialize_doc(t) for t in tutors]


def delete_tutor(tutor_collection, tutor_id: str) -> DeleteResult:
    """
    Ištrina korepetitorių iš DB pagal _id.
    """
    return tutor_collection.delete_one({"_id": ObjectId(tutor_id)})

def remove_student_from_tutor(
    tutor_collection,
    tutor_email: str,
    student_id: str
) -> dict:
    """
    Pašalina studentą iš konkretaus korepetitoriaus students_subjects pagal student_id.
    """
    result: UpdateResult = tutor_collection.update_one(
        {"email": tutor_email},
        {"$pull": {"students_subjects": {"student_id": student_id}}}
    )

    if result.modified_count == 1:
        return {"removed": True}
    else:
        return {"removed": False}

if __name__ == "__main__":
    db = get_db()
    tutor_collection = db['tutor']

