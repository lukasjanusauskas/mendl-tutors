from datetime import datetime
import hashlib
import json

from connection import get_db


def parse_date_of_birth(dob: str) -> datetime:
    """ Parses date of birth, if correct, returns ValueError, if incorrect. """

    try:
        date_of_birth = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        print(f'date of birth is of the wrong format: {dob}')
        raise ValueError()
    
    if date_of_birth > datetime.now():
        raise ValueError(f"date of birth value is incorrect: {dob}")

    return date_of_birth


def create_new_tutor(
    full_name: str,
    dob: str,
    email: str,
    password: str,
    phone_number: str | None = None,
) -> dict:
    """ Creates a tutor from given information. """

    dob = parse_date_of_birth(dob)
    password_encoded = password.encode( 'utf-8' )

    hash_algo = hashlib.sha256()
    hash_algo.update( password_encoded )
    password_encrypted = hash_algo.hexdigest()

    tutor = {
        'full_name': full_name,
        'dob': dob,
        'email': email,
        'password_encrypted': password_encrypted,
        'number_of_lessons': 0,
        'students_subjects': []
    }

    if phone_number is not None:
        tutor['phone_number'] = phone_number

    return tutor

if __name__ == "__main__":
    tutor0 = create_new_tutor(
        'Jonas Jonaitis',
        '2004-08-07',
        email='jonas.jonaitis@mail.lt',
        password='1234'
    )

    db = get_db()
    db['tutor'].insert_one(tutor0)

    print('TUTORS:\n')
    cursor = db['tutor'].find({})
    for doc in cursor:
        print(doc)