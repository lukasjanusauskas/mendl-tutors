import clickhouse_connect
import pandas as pd
from clickhouse.clickhouse_config import USERNAME, PASSWORD, HOST
from api.reviews import avg_rating_student_tutor


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=HOST, user=USERNAME, password=PASSWORD, secure=True
    )


def add_student_clickhouse(client, first_name, last_name, class_num, school_name, date_of_birth):
    """Prideda studentą į ClickHouse"""

    # Gauname school_sk pagal school_name
    school_result = client.query(f"SELECT school_sk FROM dim_schools WHERE name = '{school_name}'")
    if not school_result.result_set or not school_result.result_set[0]:
        raise ValueError(f"Mokykla su vardu '{school_name}' nerasta ClickHouse lenteleje dim_schools")

    school_sk = school_result.result_set[0][0]

    # Randame naują student_sk
    result = client.query("SELECT MAX(student_sk) FROM dim_students")
    next_student_sk = result.result_set[0][0] + 1 if result.result_set[0][0] is not None else 1

    # Sukuriame naują studento įrašą
    new_student = pd.DataFrame(
        {
            "student_sk": [next_student_sk],
            "first_name": [first_name],
            "last_name": [last_name],
            "class": [class_num],
            "school_fk": [school_sk],
            "date_of_birth": [pd.to_datetime(date_of_birth).date()],  # tik data
        }
    )

    # Įterpiame į dim_students
    client.insert_df("dim_students", new_student)
    return next_student_sk


def delete_student_clickhouse(client, first_name, last_name):
    """
    Ištrina studentą iš ClickHouse pagal vardą, pavardę
    Grąžina True, jei studentas buvo rastas ir ištrintas, False – jei nerastas.
    """

    # Surandame student_sk
    query = f"SELECT student_sk FROM dim_students WHERE first_name = '{first_name}' AND last_name = '{last_name}'"


    result = client.query(query)
    if not result.result_set or not result.result_set[0]:
        # Studentas nerastas
        return False

    student_sk = result.result_set[0][0]

    # Ištriname studentą pagal student_sk
    client.command(f"ALTER TABLE dim_students DELETE WHERE student_sk = {student_sk}")

    return True


def add_tutor_clickhouse(client, first_name, last_name, date_of_birth):
    """Prideda korepetitorių į clickhouse"""

    result = client.query("SELECT MAX(tutor_sk) FROM dim_tutors")
    next_tutor_sk = result.result_set[0][0] + 1

    new_tutor = pd.DataFrame(
        {
            "tutor_sk": [next_tutor_sk],
            "first_name": [first_name],
            "last_name": [last_name],
            "date_of_birth": [pd.to_datetime(date_of_birth)],
        }
    )

    client.insert_df("dim_tutors", new_tutor)
    return next_tutor_sk


def delete_tutor_clickhouse(client, first_name, last_name, date_of_birth=None):
    """
    Ištrina korepetitorių iš ClickHouse pagal vardą, pavardę
    Grąžina True, jei korepetitorius buvo rastas ir ištrintas, False – jei nerastas.
    """

    # Surandame tutor_sk
    query = f"SELECT tutor_sk FROM dim_tutors WHERE first_name = '{first_name}' AND last_name = '{last_name}'"


    result = client.query(query)
    if not result.result_set or not result.result_set[0]:
        # Korepetitorius nerastas
        return False

    tutor_sk = result.result_set[0][0]

    # Ištriname korepetitorių pagal tutor_sk
    client.command(f"ALTER TABLE dim_tutors DELETE WHERE tutor_sk = {tutor_sk}")

    return True



from bson import ObjectId

def get_student_fk_clickhouse(client, student_id, db):
    """
    Pagal MongoDB student_id suranda student_fk (student_sk) ClickHouse dim_students.
    Grąžina student_sk, arba None, jei nerasta.
    """
    # Gauname studentą iš MongoDB
    student = db.student.find_one({"_id": ObjectId(student_id)})
    if not student:
        return None

    first_name = student.get("first_name")
    last_name = student.get("last_name")
    date_of_birth = student.get("date_of_birth")
    class_num = student.get("class")

    # Surandame student_sk ClickHouse pagal first_name, last_name
    query = f"SELECT student_sk FROM dim_students WHERE first_name = '{first_name}' AND last_name = '{last_name}'"
    if date_of_birth:
        dob_str = pd.to_datetime(date_of_birth).date()
        query += f" AND date_of_birth = '{dob_str}'"
    if class_num:
        query += f" AND class = {class_num}"

    result = client.query(query)
    if not result.result_set or not result.result_set[0]:
        return None

    return result.result_set[0][0]


def get_tutor_fk_clickhouse(client, tutor_id, db):
    """
    Pagal MongoDB tutor_id suranda tutor_fk (tutor_sk) ClickHouse dim_tutors.
    Grąžina tutor_sk, arba None, jei nerasta.
    """
    # Gauname korepetitorių iš MongoDB
    tutor = db.tutor.find_one({"_id": ObjectId(tutor_id)})
    if not tutor:
        return None

    first_name = tutor.get("first_name")
    last_name = tutor.get("last_name")
    date_of_birth = tutor.get("date_of_birth")

    # Surandame tutor_sk ClickHouse pagal first_name
    query = f"SELECT tutor_sk FROM dim_tutors WHERE first_name = '{first_name}' AND last_name = '{last_name}'"
    if date_of_birth:
        dob_str = pd.to_datetime(date_of_birth).date()
        query += f" AND date_of_birth = '{dob_str}'"

    result = client.query(query)
    if not result.result_set or not result.result_set[0]:
        return None

    return result.result_set[0][0]


def get_subject_sk_clickhouse(client, subject_name):
    """
    Pagal subject_name suranda subject_sk iš d_subject lentelės ClickHouse.
    Grąžina subject_sk arba None, jei nerasta.
    """
    query = f"SELECT subject_sk FROM dim_subjects WHERE name = '{subject_name}'"
    result = client.query(query)

    if not result.result_set or not result.result_set[0]:
        return None

    return result.result_set[0][0]


def f_student_tutor_stat_add(client, student_id, tutor_id, subject_name, db, rating=None, date=None, lessons=None):
    """
    Prideda įrašą į ClickHouse lentelę f_student_tutor_stat su raktiniais student, tutor ir subject.
    rating ir date yra opcionalūs papildomi laukai.
    """

    # Gauname student_fk
    student_fk = get_student_fk_clickhouse(client, student_id, db)
    if student_fk is None:
        raise ValueError(f"Studentas su id {student_id} ClickHouse nerastas.")

    # Gauname tutor_fk
    tutor_fk = get_tutor_fk_clickhouse(client, tutor_id, db)
    if tutor_fk is None:
        raise ValueError(f"Korepetitorius su id {tutor_id} ClickHouse nerastas.")

    # Gauname subject_sk
    subject_sk = get_subject_sk_clickhouse(client, subject_name)
    if subject_sk is None:
        raise ValueError(f"Dalykas '{subject_name}' ClickHouse nerastas.")

    # Sukuriame DataFrame naujam įrašui
    new_record = pd.DataFrame(
        {
            "student_fk": [student_fk],
            "tutor_fk": [tutor_fk],
            "subject_fk": [subject_sk],
            "total_lessons": [lessons if lessons is not None else 0],
            'rating' : [rating],
            "studied_with_tutor_from": [pd.to_datetime(date) if date else pd.Timestamp.now()],
            "studied_with_tutor_to": [None]
        }
    )

    # Įterpiame į f_student_tutor_stat
    client.insert_df("f_student_tutor_stat", new_record)
    return True

def update_studied_with_tutor_to(client, student_id, tutor_id, db):
    """
    Atnaujina studied_with_tutor_to į dabartinę datą ClickHouse lentelėje f_student_tutor_stat
    pagal student_fk, tutor_fk ir opcionaliai subject_fk.
    """

    # Gauname student_fk
    student_fk = get_student_fk_clickhouse(client, student_id, db)
    if student_fk is None:
        raise ValueError(f"Studentas su id {student_id} ClickHouse nerastas.")

    # Gauname tutor_fk
    tutor_fk = get_tutor_fk_clickhouse(client, tutor_id, db)
    if tutor_fk is None:
        raise ValueError(f"Korepetitorius su id {tutor_id} ClickHouse nerastas.")

    # Sukuriame sąlygą WHERE
    conditions = [f"student_fk = {student_fk}", f"tutor_fk = {tutor_fk}"]
    where_clause = " AND ".join(conditions)

    # Atnaujiname studied_with_tutor_to į dabartinę datą
    client.command(
        f"ALTER TABLE f_student_tutor_stat UPDATE studied_with_tutor_to = now() WHERE {where_clause}"
    )

    return True

def update_student_tutor_rating(clickhouse_client, student_id, tutor_id, mongo_db, review_collection):

    avg_rating = avg_rating_student_tutor(
        review_collection,
        student_id,
        tutor_id
    )

    student_fk = get_student_fk_clickhouse(clickhouse_client, student_id, mongo_db)

    tutor_fk = get_tutor_fk_clickhouse(clickhouse_client, tutor_id, mongo_db)

    clickhouse_client.command(
        f"ALTER TABLE f_student_tutor_stat UPDATE rating = {round(avg_rating, 2)} WHERE student_fk = {student_fk} AND tutor_fk = {tutor_fk}"
    )

    return True

def update_student_tutor_lesson_count(ch, tutor_id : str, student_ids: list[str], db, lesson):
    tutor_fk = get_tutor_fk_clickhouse(ch, tutor_id, db)
    if tutor_fk is None:
        raise ValueError(f"Tutor ID {tutor_id} nerastas dim_tutors lentelėje")

    for student_id in student_ids:

        student_fk = get_student_fk_clickhouse(ch, student_id, db)
        if student_fk is None:
            print(f"⚠ Student ID {student_id} nerastas – praleidžiam")
            continue

        existing = ch.query(f"""
            SELECT total_lessons FROM f_student_tutor_stat
            WHERE student_fk = {student_fk} AND tutor_fk = {tutor_fk}
        """).result_rows

        if existing:
            current = existing[0][0] + lesson
            ch.query(f"""
                ALTER TABLE f_student_tutor_stat
                UPDATE total_lessons = {current}
                WHERE student_fk = {student_fk} AND tutor_fk = {tutor_fk}
            """)
            print(f"🔄 Student {student_fk} + Tutor {tutor_fk} → total_lessons {current}")
        else:
            ch.insert(
                "f_student_tutor_stat",
                [[student_fk, tutor_fk, 1]],
                column_names=["student_fk", "tutor_fk", "total_lessons"]
            )
            print(f"Sukurtas naujas įrašas Student {student_fk} + Tutor {tutor_fk}")



if __name__ == "__main__":
    client = get_clickhouse_client()
    """
    student_id = add_student(
        client=client,
        first_name="desimtokas",
        last_name="desimtokas",
        class_num=10,
        school_fk=1,
        date_of_birth="2011-11-11",
    )

    # remove_student(client, student_id)

    tutor_id = add_tutor(
        client=client,
        first_name="korepetitoriusnaujas",
        last_name="korepetitorius",
        date_of_birth="1980-06-07",
    )

    # remove_tutor(client, tutor_id)
    """
    from pymongo import MongoClient
    import os
    from dotenv import load_dotenv

    load_dotenv()

    clickhouse_client = get_clickhouse_client()
    mongo_client = MongoClient(os.getenv('MONGO_URI'))
    mongo_db = mongo_client['mendel-tutor']

    update_student_tutor_rating(
        clickhouse_client=clickhouse_client,
        student_id="68e820f346cf624b879fc7dc",
        tutor_id="68e3bec9ebc0938f8d678529",
        mongo_db=mongo_db,
        review_collection=mongo_db['review']
    )