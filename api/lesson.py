from utils import (
    serialize_doc,
    parse_date_of_birth,
    parse_time_of_lesson,
    generate_lesson_id_link
)
from connection import get_db
from pymongo.results import (
    InsertOneResult,
    UpdateResult,
    DeleteResult
)
import re
from bson import ObjectId
from datetime import timedelta, datetime

def create_lesson(
    lesson_collection, 
    tutor_collection,
    student_collection,
    lesson_info: dict
) -> InsertOneResult:
    """ Create a new lesson. """
    lesson: dict = {}

    # Tikriname privalomus laukus
    required_arguments = ['time', 'tutor_id', 'student_ids', 'subject']
    for field in required_arguments:
        if field not in lesson_info:
            raise KeyError(f'Truksta {field}')
        lesson[field] = lesson_info[field]

    # Paversti lesson time i datetime
    lesson['time'] = parse_time_of_lesson(lesson['time'])

    # Tikrinama, ar korepetitorius ir mokiniai yra koleckijose
    tutor = tutor_collection.find_one({'_id': ObjectId(lesson['tutor_id']) })
    if not tutor:
        raise ValueError('Korepetitoriaus el. paštas neegizstuoja')

    # Tikriname, ar mokytojas neturi pamokos tokiu laiku
    lessons_of_tutor_at_time = lesson_collection.find_one({
        'tutor.tutor_id': tutor['_id'],
        'time': lesson['time']
    })
    if lessons_of_tutor_at_time:
        raise ValueError('Laikas persidengia korepetitoriui')

    lesson['students'] = []
    for student_id in lesson['student_ids']:

        # Patikrinti ar egzistuoja
        student_id = ObjectId(student_id)
        student = student_collection.find_one({'_id': student_id})
        if not student:
            raise ValueError(f'Studentas {student_id} neegzistuoja')

        # Atrinkti informacija
        lesson['students'].append({
            'student_id': student_id,
            'first_name': student['first_name'],
            'last_name': student['last_name'],
            'parents_phone_numbers': student['parents_phone_numbers'],
            'price': 30.0,
            'paid': True,
            'moved': False
        })

    # Atrinkti informacija mokytojo
    lesson['tutor'] = {
        'tutor_id': tutor['_id'],
        'first_name': tutor['first_name'],
        'last_name': tutor['last_name']
    }

    # Patikrinti, ar mokinys priklauso mokytojui
    student_ids_tutor = [ stud['student']['student_id'] 
        for stud in tutor['students_subjects'] ]

    for student_id in lesson['student_ids']:
        if student_id not in student_ids_tutor:
            raise ValueError(f'Vienas is mokiniu nepriklauso korepetitoriui')

    # Tikriname, ar mokiniai neturi pamokos tokiu laiku
    for student_id in lesson['student_ids']:
        # Find lesson with student and time
        query = {
            "students.student_id": student_id,
            "time": lesson_info['time']
        }

        if lesson_collection.find_one(query):
            raise ValueError(f"Mokinys {student['first_name']} {student['last_name']} turi pamoką tuo laiku")

    # Generuoti pamokos id
    lesson['link'] = generate_lesson_id_link()
    lesson['type'] = 'ACTIVE'

    # Trinti nereikalingu
    del lesson['student_ids']
    del lesson['tutor_id']

    return lesson_collection.insert_one(lesson)


def add_student_to_lesson(
    lesson_collection,
    student_collection,
    lesson_id: str,
    student_id: str,
) -> dict:
    """ Add a student to an existing lesson. """

    # Rasti pamoką ir mokinį
    lesson = lesson_collection.find_one({'_id': ObjectId(lesson_id)})
    student = student_collection.find_one({'_id': ObjectId(student_id)})

    if not lesson:
        raise ValueError('Did not find lesson by id')
    elif not student:
        raise ValueError('Did not find student by id')

    # Patikrinti, ar mokinio dar nėra
    for student_in_lesson in lesson['students']:
        if student_in_lesson['student_id'] == student['_id']:
            raise ValueError(f'Mokinys {student["first_name"]} {student["last_name"]} jau yra pamokoje.')

    student_info = {
        'student_id': student['_id'],
        'first_name': student['first_name'],
        'last_name': student['last_name'],
        'parents_phone_numbers': student['parents_phone_numbers'],
        'price': 30.0,
        'paid': True,
        'moved': False
    }

    return lesson_collection.find_one_and_update(
        {'_id': ObjectId(lesson_id)},
        {'$push': {'students': student_info}}
    )


def change_lesson_date(
    lesson_collection,
    lesson_id: str,
    time: str
) -> dict:
    """ Move a lesson to a different date. """

    time_parsed = parse_time_of_lesson(time)
    return lesson_collection.find_one_and_update(
        {'_id': ObjectId(lesson_id)},
        { "$set": {'time': time_parsed} }
    )


def delete_lesson(
    lesson_collection,
    lesson_id: str
) -> dict:
    """ Delete a lesson by setting its type, not by physically deleting it. """

    # Find lesson
    lesson = lesson_collection.find_one( {'_id': ObjectId(lesson_id)} )

    # Check if lesson is not deleted and only then end
    if 'type' in lesson:
        if lesson['type'] == 'DELETED':
            return

    return lesson_collection.find_one_and_update(
        { "_id": ObjectId(lesson_id) },
        { "$set": {"type": "DELETED"} }
    )


def list_lessons_tutor_week(
    lesson_collection,
    tutor_collection,
    tutor_id: str
) -> list[dict]:
    """ List tutor's lessons. """

    # Patikrinti, ar toks korepetitoriaus id yra
    if not tutor_collection.find_one({'_id': ObjectId(tutor_id)}):
        raise ValueError('Specified tutor could not be found')

    # Grazinti informacija
    lessons = []

    query = {
        'tutor.tutor_id': ObjectId(tutor_id),
        'time': {
            "$gt": datetime.now(),
            "$lt": datetime.now() + timedelta(weeks=1)
        },
        # Jei "type" neegzistuoja - pamoka aktyvi, jei "type" != "DELETED" irgi aktyvi.
        "$or": [
            {"type": {"exists": False}},
            {"type": {"$ne": "DELETED"}}
        ]
    }

    for lesson_doc in lesson_collection.find(query):
        students = [
            {'first_name': stud['first_name'], 'last_name': stud['last_name']}
            for stud in lesson_doc['students']
        ]

        lessons.append({
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link']
        })

    return lessons


def list_lessons_tutor_month(
    lesson_collection,
    tutor_collection,
    tutor_id: str,
    year: str,
    month: str 
) -> list[dict]:
    """ List tutor's lessons. """

    # Patikrinti, ar toks korepetitoriaus id yra
    if not tutor_collection.find_one({'_id': ObjectId(tutor_id)}):
        raise ValueError('Specified tutor could not be found')

    try:
        year = int(year)
        month = int(month)
    except ValueError:
        raise ValueError('Could not convert year or month (arguments 2 and 3) to int')

    # Grazinti informacija
    lessons = []

    query = {
        'tutor.tutor_id': ObjectId(tutor_id),
        'time': {
            "$gte": datetime(year, month, 1),
            "$lt": datetime(year, month+1, 1)
        }
    }
    for lesson_doc in lesson_collection.find(query):
        students = [
            {'first_name': stud['first_name'], 'last_name': stud['last_name']}
            for stud in lesson_doc['students']
        ]

        lessons.append({
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link']
        })

        if 'type' in lesson_doc:
            lessons[-1] = lessons[-1] | {"type": lesson_doc["type"]}

    return lessons


def list_lessons_student_week(
    lesson_collection,
    student_collection,
    student_id: str
):
    """ List student's lesson """

    # Patikrinti, ar toks korepetitoriaus id yra
    if not student_collection.find_one({'_id': ObjectId(student_id)}):
        raise ValueError('Specified student could not be found')

    # Grazinti informacija
    lessons = []

    query = {
        'students.student_id': ObjectId(student_id),
        'time': {
            "$gt": datetime.now(),
            "$lt": datetime.now() + timedelta(weeks=1)
        },
        # Jei "type" neegzistuoja - pamoka aktyvi, jei "type" != "DELETED" irgi aktyvi.
        "$or": [
            {"type": {"exists": False}},
            {"type": {"$ne": "DELETED"}}
        ]
    }

    for lesson_doc in lesson_collection.find(query):
        students = [
            {'first_name': stud['first_name'], 'last_name': stud['last_name']}
            for stud in lesson_doc['students']
        ]

        lessons.append({
            'tutor_first_name': lesson_doc['tutor']['first_name'],
            'tutor_last_name': lesson_doc['tutor']['last_name'],
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link']
        })

    return lessons


def list_lesson_student_month(
    lesson_collection,
    student_collection,
    student_id: str,
    year: str,
    month: str 
):
    """ List student's lesson """

    # Patikrinti, ar toks korepetitoriaus id yra
    if not student_collection.find_one({'_id': ObjectId(student_id)}):
        raise ValueError('Specified student could not be found')

    try:
        year = int(year)
        month = int(month)
    except ValueError:
        raise ValueError('Could not convert year or month (arguments 2 and 3) to int')

    # Grazinti informacija
    lessons = []

    query = {
        'students.student_id': ObjectId(student_id),
        'time': {
            "$gte": datetime(year, month, 1),
            "$lt": datetime(year, month+1, 1)
        }
    }
    for lesson_doc in lesson_collection.find(query):
        students = [
            {'first_name': stud['first_name'], 'last_name': stud['last_name']}
            for stud in lesson_doc['students']
        ]

        lessons.append({
            'tutor_first_name': lesson_doc['tutor']['first_name'],
            'tutor_last_name': lesson_doc['tutor']['last_name'],
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link']
        })

        if 'type' in lesson_doc:
            lessons[-1] = lessons[-1] | {"type": lesson_doc["type"]}

    return lessons


# def change_lesson_info_for_student(
#     lesson_collection,
#     tutor_collection,
#     lesson_change_info: dict
# ):
#     """ Change price for student """


if __name__ == "__main__":
    db = get_db()
    
    lesson_collection = db['lesson']
    student_collection = db['student']
    tutor_collection = db['tutor']