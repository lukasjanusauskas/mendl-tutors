from datetime import datetime
from connection import get_db
from tutor import parse_date_of_birth
from pymongo.results import (
    InsertOneResult,
    UpdateResult
)

def create_new_student(
    student_collection,
    student_info: dict
) -> InsertOneResult:
    """
    Sukurti studenta ir issaugoti i duombaze.
    Grazina InsertOneResult su inserted_id ir acknowledged.
    """


    student: dict = {}


    required_arguments = ['full_name', 'dob', 'class', 'subjects', 'parents_phone_number']
    for field in required_arguments:
        if field not in student_info:
            raise KeyError(f'Truksta {field}')
        student[field] = student_info[field]


    optional_arguments = ['phone_number', 'student_email', 'parents_email']
    for field in optional_arguments:
        if field in student_info:
            student[field] = student_info[field]


    student['dob'] = parse_date_of_birth(student_info['dob'])


    if not isinstance(student['subjects'], list) or len(student['subjects']) == 0:
        raise ValueError("subjects turi buti ne tuscias masyvas")



    return student_collection.insert_one(student)

if __name__ == "__main__":
    db = get_db()
    student_collection = db['student']