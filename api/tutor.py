"""
Tutor can be:
- added
- assign/remove students
- add or update phone/email
- update fields (email)
"""

from api.utils import (
    serialize_doc,
    parse_date_of_birth
)
import hashlib
from redis_api.redis_client import get_redis
from redis.exceptions import LockError

redis_client = get_redis()
from pymongo.results import (
    InsertOneResult,
    UpdateResult,
    DeleteResult
)

from api.connection import get_db
import re
from bson import ObjectId

def create_new_tutor(tutor_collection, tutor_info: dict) -> InsertOneResult:
    """
    Sukurti korepetitoriu ir įrašyti į duombazę.
    Grazina InsertOneResult su inserted_id ir acknowledged.
    Patikrina ar toks korepetitorius jau egzistuoja (pagal full_name ir gimimo datą).
    """
    lock = redis_client.lock("tutors:write", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Korepetitorių sąrašas šiuo metu redaguojamas")
    
    try:
        tutor: dict = {}

        # 1️⃣ Tikriname privalomus laukus
        required_arguments = [
            'first_name', 'last_name', 'date_of_birth', 'email', 'password', 'subjects']
        for field in required_arguments:
            if field not in tutor_info:
                raise KeyError(f'Truksta {field}')
            tutor[field] = tutor_info[field]

        # 2️⃣ Tikriname papildomus laukus
        optional_parameters = ['phone_number', 'second_name']
        for field in optional_parameters:
            if field in tutor_info:
                tutor[field] = tutor_info[field]

        # 3️⃣ Konvertuojame gimimo datą į datetime objektą
        date_of_birth_date = parse_date_of_birth(tutor_info['date_of_birth'])
        tutor['date_of_birth'] = date_of_birth_date

        # # 4️⃣ Patikriname, ar toks tutor jau egzistuoja (full_name + date_of_birth)
        # # Nemanau, kad reikia sekancio:
        # date_of_birth_start = date_of_birth_date
        # date_of_birth_end = date_of_birth_start + timedelta(days=1)
        # existing_tutor = tutor_collection.find_one({
        #     "full_name": tutor['full_name'],
        #     "date_of_birth": {"$gte": date_of_birth_start, "$lt": date_of_birth_end}
        # })
        # if existing_tutor:
        #     raise ValueError("Korepetitorius su tokiu vardu ir gimimo data jau egzistuoja!")

        # Uztikrinti, kad max_class nebutu tuscias. Jei nera irodyta, padaroma 12
        for subject in tutor['subjects']:
            if 'max_class' not in subject:
                subject['max_class'] = 12

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
        tutor['password_hashed'] = hash_algo.hexdigest()
        del tutor['password']

        # 8️⃣ Papildomi laukai
        tutor['students_subjects'] = []

        # 9️⃣ Įrašome į DB
        result = tutor_collection.insert_one(tutor)
        return result
    finally:
        try:
            lock.release()
        except:
            pass


def assign_student_to_tutor(
    tutor_collection,
    student_collection,
    tutor_id: str,
    student_id: str,
    subject: str
) -> UpdateResult:
    """
    Priskirti studenta prie korepetitoriaus pagal subject.
    Grazina UpdateResult su informacija apie update.
    """
    lock = redis_client.lock(f"tutor:{tutor_id}", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Korepetitorius šiuo metu redaguojamas")
    
    try:
        # 1️⃣ Paimti studenta is DB
        student = student_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            raise ValueError("Studentas su tokiu ID nerastas")

        # 2️⃣ Patikrinti ar egzistuoja korepetitorius pagal id
        tutor = tutor_collection.find_one({"_id": ObjectId(tutor_id)})
        if not tutor:
            raise ValueError("Korepetitorius su tokiu ID nerastas")

        # 3️⃣ Patikrinti ar korepetitorius moko tokio subject
        tutor_subjects = [s.get("subject") for s in tutor.get("subjects", [])]
        if subject not in tutor_subjects:
            raise ValueError("Korepetitorius nemoko sio dalyko")

        # 4️⃣ Patikrinti ar studentas jau priskirtas prie sio subject
        already_assigned = any(
            s.get("student", {}).get("student_id") == str(student["_id"]) and s.get("subject") == subject
            for s in tutor.get("students_subjects", [])
        )
        if already_assigned:
            raise ValueError("Studentas jau priskirtas prie šio dalyko")

        # 5️⃣ Sukurti įrašą studentui su class
        student_entry = {
            "student": {
                "student_id": str(student["_id"]),
                "first_name": student["first_name"],
                "last_name": student["last_name"],
                "parents_phone_numbers": student.get('parents_phone_numbers', []),
                "student_class": student.get("class")
            },
        }

        # 6️⃣ Pridėti prie tutor.students_subjects
        result = tutor_collection.update_one(
            {"_id": ObjectId(tutor_id)},
            {"$push": {"students_subjects": student_entry}}
        )
        return result
    finally:
        try:
            lock.release()
        except:
            pass

def get_tutor_students(tutor_collection, tutor_id: str) -> list[dict]:
    """
    Grazina visus tutor studentus su vardais, klase ir subjectais.
    Dirba tik su nauju students_subjects formatu ir nenaudoja student kolekcijos.
    """
    # 1️⃣ Paimame korepetitoriu pagal ID
    tutor = tutor_collection.find_one({"_id": ObjectId(tutor_id)})
    if not tutor:
        raise ValueError("Korepetitorius nerastas")

    students_subjects = tutor.get("students_subjects", [])
    results = []

    for entry in students_subjects:
        # 2️⃣ Tikriname, ar entry turi 'student' ir 'student_id'
        student_info = entry.get("student")
        if not student_info or "student_id" not in student_info:
            continue  # jei ne, praleidziame

        # 3️⃣ Gauname reikiamus duomenis tiesiai is tutor.students_subjects
        results.append({
            "student_id": student_info["student_id"],
            "first_name": student_info.get("first_name", ""),
            "last_name": student_info.get("last_name", ""),
            "student_class": student_info.get("student_class"),  # добавлено
            "subject": entry.get("subject", "-"),
            "parents_phone_numbers": student_info.get("parents_phone_numbers", [])
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

def get_tutors_by_name(tutor_collection, first_name: str, last_name: str):
    """
    Ieško korepetitorių pagal vardą ir pavardę (case-insensitive).
    """
    query = {
        "first_name": re.compile(first_name, re.IGNORECASE),
        "last_name": re.compile(last_name, re.IGNORECASE)
    }

    tutors = tutor_collection.find(query)
    return [serialize_doc(t) for t in tutors]

def find_tutors_by_subject_and_class(tutor_collection, subject, student_class):
    """
    Suranda korepetitorius pagal konkretų dalyką ir klasę.
    Grąžina sąrašą su pagrindine informacija apie korepetitorius.
    """

    # Naudojame $elemMatch, kad ieškotume dalyko masyvo viduje
    query = {
        "subjects": {
            "$elemMatch": {
                "subject": subject,
                "max_class": {"$gte": student_class}
            }
        }
    }

    # Nurodome, kokius laukus norime gauti:
    # _id paliekame, bet nerodome slaptažodžių ar kitų jautrių duomenų
    projection = {
        "_id": 1,
        "first_name": 1,
        "second_name": 1,
        "last_name": 1,
        "email": 1,
        "phone_number": 1,
        "subjects": 1,
        "rating": 1,
        "number_of_lessons": 1
    }

    # Vykdome užklausą ir paverčiame rezultatus į sąrašą
    tutors = list(tutor_collection.find(query, projection))
    return tutors

def delete_tutor(tutor_collection, tutor_id: str) -> dict:
    """
    Ištrina korepetitorių iš DB pagal _id.
    Grazina dict su info apie delete.
    """
    lock = redis_client.lock(f"tutor:{tutor_id}", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Korepetitorius šiuo metu redaguojamas")
    
    try:
        result = tutor_collection.delete_one({"_id": ObjectId(tutor_id)})
        return {"deleted": result.deleted_count == 1}
    finally:
        try:
            lock.release()
        except:
            pass

def remove_student_from_tutor(
    tutor_collection,
    tutor_id: str,
    student_id: str
) -> dict:
    """
    Pašalina studentą iš konkretaus korepetitoriaus students_subjects pagal student_id.
    """
    lock = redis_client.lock(f"tutor:{tutor_id}", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Korepetitorius šiuo metu redaguojamas")
    
    try:
        # Patikrinti ar egzistuoja tutor
        tutor = tutor_collection.find_one({'_id': ObjectId(tutor_id)})
        if not tutor:
            raise ValueError('Tokio korepetitoriaus nera')

        # Patikrinti ar studentas priklauso tutor
        students_subjects = tutor.get('students_subjects', [])
        for entry in students_subjects:
            if entry['student']['student_id'] == str(student_id):
                break
        else:
            raise ValueError('Tokio mokinio korepetitorius neturi')

        # Ištrinti studentą iš students_subjects
        result: UpdateResult = tutor_collection.update_one(
            {"_id": ObjectId(tutor_id)},
            {"$pull": {"students_subjects": {"student.student_id": str(student_id)}}}
        )

        if result.modified_count == 1:
            return {"removed": True}
        else:
            return {"removed": False}
    finally:
        try:
            lock.release()
        except:
            pass


if __name__ == "__main__":
    db = get_db()
    tutor_collection = db['tutor']

