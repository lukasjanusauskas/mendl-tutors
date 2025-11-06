from datetime import datetime
import bson
import string

BASE_URL = 'mendltutors.lt'
LINK_RANDOM_PART = 32
POSSIBLE_CHARACTERS = string.ascii_letters + string.digits


def parse_date_of_birth(dob: str) -> datetime:
    """ Patikrinti gimimo data. """

    try:
        date_of_birth = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f'gimimo metu formatas netinkamas: {dob} turi buti YYYY-MM-DD')

    if date_of_birth > datetime.now():
        raise ValueError(f"date of birth value is incorrect: {dob}")

    return date_of_birth

def serialize_doc(doc: dict) -> dict:
    """Konvertuoja ObjectId į eilutę JSON grąžinimui."""
    doc["_id"] = str(doc["_id"])
    return doc


def generate_lesson_id_link() -> str:
    lesson_id = bson.ObjectId()
    return f'{BASE_URL}/{lesson_id}'


def parse_time_of_lesson(time: str) -> datetime:

    try:
        time_lesson = datetime.strptime(time, "%Y-%m-%d %H:%M")
    except ValueError:
        raise ValueError(f'Pamokos metu formatas netinkamas: {time} turi buti YYYY-MM-DD HH:MM')

    if time_lesson < datetime.now():
        raise ValueError(f"Negalima sukurti pamokos praeityje")

    return time_lesson


def get_student_name(
    subjects_students: list[dict],
    student_id: str
) -> str:

    for student_subject in subjects_students:
        student = student_subject['student']
        print(student)

        if str(student['student_id']) == student_id:
            return f"{student['first_name']} {student['last_name']}"

    return "Neįvardytas/buvęs mokinys"