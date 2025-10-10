from api.utils import (
    parse_time_of_lesson,
    generate_lesson_id_link
)
from api.connection import get_db
from pymongo.results import InsertOneResult
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
    for student_id in lesson_info['student_ids']:

        # Patikrinti ar egzistuoja
        student_id = ObjectId(student_id)
        student = student_collection.find_one({'_id': student_id})

        if not student:
            raise ValueError(f'Studentas {student_id} neegzistuoja')

        # Patikrinti, ar klase vienoda
        if "class" not in lesson:
            lesson["class"] = student['class']

        elif lesson["class"] != student['class']:
            raise ValueError("Mokiniu klases nera vienodos, jie vienoje pamokoje negali buti")

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
    student_ids_tutor = { 
        stud['student']['student_id']: stud['subject']
        for stud in tutor['students_subjects'] 
    }

    for student_id in lesson['student_ids']:
        if str(student_id) not in student_ids_tutor.keys():
            raise ValueError(f'Vienas is mokiniu nepriklauso korepetitoriui')

        # Patikrinti, ar korepetitorius mokina mokini sito dalyko
        student_of_tutor = student_ids_tutor[student_id]
        print(student_of_tutor)
        if student_of_tutor != lesson_info['subject']:
            raise ValueError(f'Mokinio {student["first_name"]} {student["last_name"]} korepetitorius(-ė) {lesson_info["subject"]} nemokina')

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
    lesson_doc = lesson_collection.find_one({'_id': ObjectId(lesson_id)})

    # Patikrinti, ar pamokos tuo metu nera korepetitoriui ar vienam is mokiniu
    tutor_lesson_same_time = lesson_collection.find_one({
        'tutor_id': ObjectId(lesson_doc['tutor']['tutor_id']),
        'time': time_parsed
    })

    if tutor_lesson_same_time:
        raise ValueError('Korepetitorius tuo metu turi pamoka')

    for student in lesson_doc['students']:
        student_lesson_same_time = lesson_collection.find_one({
            'students.student_id': ObjectId(student['student_id']),
            'time': time_parsed
        })

        if student_lesson_same_time:
            raise ValueError(f'Mokinys {student["first_name"]} {student["last_name"]} turi pamoka tuo metu')

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
            '_id': str(lesson_doc['_id']),
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link'],
            "subject": lesson_doc['subject'],
            'class': lesson_doc['class']
        })


    lesson_list = sorted(lessons,
        key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M'))

    return lesson_list


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

        if 'type' in lesson_doc:
            if lesson_doc['type'] != 'ACTIVE':
                continue

        lessons.append({
            '_id': str(lesson_doc['_id']),
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link'],
            "subject": lesson_doc['subject'],
            'class': lesson_doc['class']
        })

    lesson_list = sorted(lessons,
        key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M'))

    return lesson_list


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
            '_id': str(lesson_doc['_id']),
            'tutor_first_name': lesson_doc['tutor']['first_name'],
            'tutor_last_name': lesson_doc['tutor']['last_name'],
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link']
        })

    lesson_list = sorted(lessons,
        key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M'))

    return lesson_list


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
            '_id': str(lesson_doc['_id']),
            'tutor_first_name': lesson_doc['tutor']['first_name'],
            'tutor_last_name': lesson_doc['tutor']['last_name'],
            'time': lesson_doc['time'].strftime('%Y-%m-%d %H:%M'),
            'students': students,
            'link': lesson_doc['link']
        })

        if 'type' in lesson_doc:
            lessons[-1] = lessons[-1] | {"type": lesson_doc["type"]}

    lesson_list = sorted(lessons,
        key=lambda x: datetime.strptime(x['time'], '%Y-%m-%d %H:%M'))

    return lesson_list


def change_lesson_price_student(
    lesson_collection,
    lesson_id: int,
    student_id: int,
    price: float
) -> dict:
    """ Change price for student """

    if price < 0.0:
        raise ValueError('Kaina turi buti bent 0')

    # Kad neuzluztu Mongo, nes nedaro type casting
    if isinstance(price, int):
        price = float(price)

    # Take the lesson
    lesson_doc = lesson_collection.find_one({'_id': ObjectId(lesson_id)})
    if not lesson_doc:
        raise ValueError('Tokios pamokos nera')

    students = []
    # Make changes if student exists
    for student in lesson_doc['students']:
        if student['student_id'] == ObjectId(student_id):
            student['price'] = price

        students.append( student )

    # Update
    return lesson_collection.find_one_and_update(
        {'_id': ObjectId(lesson_id)},
        {'$set': {'students': students}}
    )


def delete_student_from_lesson(
    lesson_collection,
    student_collection,
    lesson_id: str,
    student_id: str
) -> dict:
    
    student = student_collection.find_one({'_id': ObjectId(student_id) })
    lesson_doc = lesson_collection.find_one({'_id': ObjectId(lesson_id) })

    # Remove student
    student_list = list(filter(
        lambda student_doc: student_doc['student_id'] != ObjectId( student['_id'] ),
        lesson_doc['students']
    ))

    if len(student_list) == 0:
        delete_lesson(lesson_collection, lesson_id)

    return lesson_collection.find_one_and_update(
        {"_id": ObjectId(lesson_id)},
        { "$set": {"students": student_list} }
    )


def change_lesson_time_student(
    lesson_collection,
    tutor_collection,
    student_collection,
    lesson_info: dict
) -> dict | InsertOneResult | None:
    """
    Perkelia vieno mokinio pamokos laika.
    
    Jei tuo metu yra pamoka su tuo dalyku tam korepetitoriui, toj klasej, bet mokinio nera, perkelia.
    Jei nera pamokos tam mokiniui, korepetitoriui ir dalykui tuo metu, ji sukuriama.

    Jei sukurta pamoka -> grazina InsertOneResult
    Jei pamoka jau egzistuoja -> grazina dict
    Jei laikas sutampa su dabartine pamoka -> grazina None
    """

    # Validate fields
    required_arguments = ['time', 'lesson_id', 'student_id']
    for field in required_arguments:
        if field not in lesson_info:
            raise KeyError(f'Truksta {field}')
        lesson_info[field] = lesson_info[field]

    time = parse_time_of_lesson(lesson_info['time'])
    lesson_doc = lesson_collection.find_one({'_id': ObjectId(lesson_info['lesson_id'])})
    if not lesson_doc:
        raise ValueError('Tokios pamokos nera')

    # Jei time == dabartinis pamokos laikas, grazinti None
    if time == lesson_doc['time']:
        return

    # Surasti, ar mokinys yra pamokoje ir ji isimti
    students = []
    for student in lesson_doc['students']:
        if student['student_id'] == ObjectId( lesson_info['student_id'] ):
            continue

        students.append(student)
    
    # Jei tokio mokinio nebuvo (niekas neisimtas)
    if len(students) == len(lesson_doc['students']):
        raise ValueError('Tokio mokinio nebuvo')

    student = student_collection.find_one({"_id": ObjectId( lesson_info["student_id"] )})

    # Patikrinti, ar pamoka tokiu laiku egzistuoja korepetitoriui
    lesson_same_time_tutor = lesson_collection.find_one({
        "tutor.tutor_id": lesson_doc["tutor"]["tutor_id"],
        "time": time
    })

    # Jei korepetitorius tuo metu turi suderinama pamoka, prideti mokini
    if lesson_same_time_tutor:
        # Patikrinti klase ir dalyka ir prideti mokini. Jei neatitinka -> ValueError
        if not lesson_doc['subject'] in student["subjects"]:
            raise ValueError("Korepetitorius tuo metu turi nesuderinama pamoka")

        if lesson_doc['class'] != student['class']:
            raise ValueError("Korepetitorius tuo metu turi nesuderinama pamoka")

    # Tik dabar, kai istiknom, isimam studenta is pamokos
    delete_student_from_lesson(
        lesson_collection,
        student_collection,
        lesson_info['lesson_id'],
        lesson_info['student_id']
    )

    # Jei korepetitorius tuo metu pamokos neturi, sukurti pamoka
    if lesson_same_time_tutor:

        return add_student_to_lesson(
            lesson_collection, 
            student_collection, 
            str(lesson_doc['_id']),
            str(student['_id'])
        )

    else:
        # Paimti, tai ko reikia pamokai sukurti
        lesson_info_creation = {
            'time': lesson_info['time'],
            'tutor_id': str( lesson_doc['tutor']['tutor_id'] ),
            'student_ids': [student['_id']],
            'subject': lesson_doc['subject']
        }

        return create_lesson(
            lesson_collection,
            tutor_collection,
            student_collection,
            lesson_info_creation
        )


if __name__ == "__main__":
    db = get_db()

    lesson_collection = db['lesson']
    student_collection = db['student']
    tutor_collection = db['tutor']

    required_arguments = [
        'time',
        'tutor_id', 
        'student_ids',
        'subject'
    ]

    for i in range(13, 30, 7):

        create_lesson(
            db['lesson'],
            db['tutor'],
            db['student'],
            lesson_info={
                'time': f'2025-10-{i} 15:00',
                'tutor_id': '68e3cedf7249569216674679',
                'student_ids': [
                    '68dfe5e166fb223bfcdd8807'
                ],
                'subject': 'Matematika'
            }
        )
