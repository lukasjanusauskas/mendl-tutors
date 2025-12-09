import clickhouse_connect
import pandas as pd
from clickhouse.clickhouse_config import USERNAME, PASSWORD, HOST


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=HOST, user=USERNAME, password=PASSWORD, secure=True
    )


def add_student_clickhouse(client, first_name, last_name, class_num, school_name, date_of_birth):
    """Prideda studentą į ClickHouse"""

    # Gauname school_sk pagal school_name
    school_result = client.query(f"SELECT school_sk FROM d_schools WHERE name = '{school_name}'")
    if not school_result.result_set or not school_result.result_set[0]:
        raise ValueError(f"Mokykla su vardu '{school_name}' nerasta ClickHouse lenteleje d_schools")

    school_sk = school_result.result_set[0][0]

    # Randame naują student_sk
    result = client.query("SELECT MAX(student_sk) FROM d_students")
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

    # Įterpiame į d_students
    client.insert_df("d_students", new_student)
    return next_student_sk


def delete_student_clickhouse(client, first_name, last_name):
    """
    Ištrina studentą iš ClickHouse pagal vardą, pavardę
    Grąžina True, jei studentas buvo rastas ir ištrintas, False – jei nerastas.
    """

    # Surandame student_sk
    query = f"SELECT student_sk FROM d_students WHERE first_name = '{first_name}' AND last_name = '{last_name}'"


    result = client.query(query)
    if not result.result_set or not result.result_set[0]:
        # Studentas nerastas
        return False

    student_sk = result.result_set[0][0]

    # Ištriname studentą pagal student_sk
    client.command(f"ALTER TABLE d_students DELETE WHERE student_sk = {student_sk}")

    return True


def add_tutor_clickhouse(client, first_name, last_name, date_of_birth):
    """Prideda korepetitorių į clickhouse"""

    result = client.query("SELECT MAX(tutor_sk) FROM d_tutors")
    next_tutor_sk = result.result_set[0][0] + 1

    new_tutor = pd.DataFrame(
        {
            "tutor_sk": [next_tutor_sk],
            "first_name": [first_name],
            "last_name": [last_name],
            "date_of_birth": [pd.to_datetime(date_of_birth)],
        }
    )

    client.insert_df("d_tutors", new_tutor)
    return next_tutor_sk


def delete_tutor_clickhouse(client, first_name, last_name, date_of_birth=None):
    """
    Ištrina korepetitorių iš ClickHouse pagal vardą, pavardę
    Grąžina True, jei korepetitorius buvo rastas ir ištrintas, False – jei nerastas.
    """

    # Surandame tutor_sk
    query = f"SELECT tutor_sk FROM d_tutors WHERE first_name = '{first_name}' AND last_name = '{last_name}'"


    result = client.query(query)
    if not result.result_set or not result.result_set[0]:
        # Korepetitorius nerastas
        return False

    tutor_sk = result.result_set[0][0]

    # Ištriname korepetitorių pagal tutor_sk
    client.command(f"ALTER TABLE d_tutors DELETE WHERE tutor_sk = {tutor_sk}")

    return True


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