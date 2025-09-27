"""
Tutor can be:
- added
- assign/remove students
- add or update phone/email
- update fields (email)
"""

from datetime import datetime
import hashlib
from pymongo.results import (
    InsertOneResult,
    UpdateResult
)

from connection import get_db


def parse_date_of_birth(dob: str) -> datetime:
    """ Patikrinti gimimo data. """

    try:
        date_of_birth = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f'gimimo metu formatas netinkamas: {dob} turi buti YYYY-MM-DD')
    
    if date_of_birth > datetime.now():
        raise ValueError(f"date of birth value is incorrect: {dob}")

    return date_of_birth


def create_new_tutor(
    tutor_collection,
    tutor_info: dict
) -> InsertOneResult:
    """
    Sukurti korepetitoriu ir pushinti i duombaze.
    Grazina InsertOneResult - objekta su inserted_id ir acknowledged.
    """

    # Sukuriam nauja tutor dict, kad butu galima prideti fields
    tutor: dict = {}

    required_arguments = ['full_name', 'dob', 'email', 'password']
    for field in required_arguments:
        if field not in tutor_info:
            raise KeyError(f'Truksta {field}')

        tutor[field] = tutor_info[field]

    optional_parameters = ['phone_number']
    for field in optional_parameters:
        if field in tutor_info:
            tutor[field] = tutor_info[field]

    # Patikriname, ar email unikalus
    filter_email = {'email': tutor_info['email']}
    if tutor_collection.find_one(filter_email) is not None:
        raise ValueError('email turi buti unikalus')

    # Patikrinam date of birth
    tutor['dob'] = parse_date_of_birth(tutor_info['dob'])

    # Hashinti slaptazodzius
    password_encoded = tutor['password'].encode( 'utf-8' )
    hash_algo = hashlib.sha256()
    hash_algo.update( password_encoded )

    tutor['password_encrypted'] = hash_algo.hexdigest()
    del tutor['password']

    # Prideti fields, kuriu reikes
    tutor['students_subjects'] = []
    tutor['number_of_lessons'] = 0

    return tutor_collection.insert_one(tutor)


def assign_student_to_tutor(
    tutor_email: str,
    student_id: str,
    subject: str
) -> UpdateResult:
    # Paimti studenta ir isrinkti informacija

    # Prideti, jei dar nepridetas

    pass

if __name__ == "__main__":
    db = get_db()
    tutor_collection = db['tutor']