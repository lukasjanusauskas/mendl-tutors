from api.utils import (
    serialize_doc,
    parse_date_of_birth
)
from api.connection import get_db
from redis_api.redis_client import get_redis
from redis.exceptions import LockError

redis_client = get_redis()
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
    lock = redis_client.lock("students:write", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Mokinių sąrašas šiuo metu redaguojamas")

    try:
        student: dict = {}

        # Tikriname privalomus laukus
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

        # Tikriname papildomus laukus
        optional_arguments = ['student_phone_number', 'student_email', 'parents_email', 'second_name']
        for field in optional_arguments:
            if field in student_info:
                student[field] = student_info[field]

        # Konvertuojame gimimo datą į datetime
        date_of_birth_date = parse_date_of_birth(student_info['date_of_birth'])
        student['date_of_birth'] = date_of_birth_date

        # Tikriname subjects
        if not isinstance(student['subjects'], list) or len(student['subjects']) == 0:
            raise ValueError("subjects turi buti ne tuscias masyvas")

        # Tikriname, ar toks studentas jau egzistuoja (first_name + date_of_birth)
        date_of_birth_start = date_of_birth_date
        date_of_birth_end = date_of_birth_start + timedelta(days=1)
        existing_student = student_collection.find_one({
            "first_name": student['first_name'],
            "date_of_birth": {"$gte": date_of_birth_start, "$lt": date_of_birth_end},
        })
        if existing_student:
            raise ValueError("Toks mokinys jau egzistuoja!")

        password_encoded = student['password'].encode('utf-8')
        hash_algo = hashlib.sha256()
        hash_algo.update(password_encoded)
        student['password_hashed'] = hash_algo.hexdigest()
        del student['password']

        # Įrašome į DB
        result = student_collection.insert_one(student)
        return result
    finally:
        try:
            lock.release()
        except:
            pass


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
    lock = redis_client.lock(f"student:{student_id}", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Mokinys šiuo metu redaguojamas")

    try:
        result: DeleteResult = student_collection.delete_one({"_id": ObjectId(student_id)})

        if result.deleted_count == 1:
            # ištrinam studentą iš visų tutor.students_subjects
            tutor_collection.update_many(
                {},
                {"$pull": {"students_subjects": {"student.student_id": student_id}}}
            )
            return {"deleted": True}
        else:
            return {"deleted": False}
    finally:
        try:
            lock.release()
        except:
            pass


def get_students_tutors(
        tutor_collection,
        student_id: str
):
    # Run a query to take all tutors with this student
    query_res = tutor_collection.find({
        "students_subjects.student.student_id": student_id
    })

    tutors = []
    for tutor_doc in query_res:
        tutors.append(tutor_doc)

    assert len(tutors) > 0, "Mokinys neturi priskirtų mokinių"

    return tutors


def remove_tutor_from_student(student_collection, tutor_id: str, student_id: str) -> dict:
    """
    Pašalina nuorodą į korepetitorių studento dokumente.
    Naudoja Redis užraktą ant studento įrašo.
    Grąžina {'removed': True/False}
    """
    lock = redis_client.lock(f"student:{student_id}", timeout=10)
    if not lock.acquire(blocking=True, blocking_timeout=5):
        raise LockError("Mokinys šiuo metu redaguojamas")

    try:
        update_res = student_collection.update_one(
            {"_id": ObjectId(student_id)},
            {
                "$pull": {
                    "tutor_ids": tutor_id,
                    "tutors": {"tutor_id": tutor_id},
                    "assigned_tutors": tutor_id
                }
            }
        )

        return {"removed": update_res.modified_count > 0}

    finally:
        try:
            lock.release()
        except:
            pass


if __name__ == "__main__":
    db = get_db()
    student_collection = db['student']
    tutor_collection = db['tutor']

    print(get_students_tutors(tutor_collection, "68dfe5e166fb223bfcdd8807"))