import clickhouse_connect
import pandas as pd
from clickhouse.clickhouse_config import USERNAME, PASSWORD, HOST


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=HOST, user=USERNAME, password=PASSWORD, secure=True
    )


def add_student(client, first_name, last_name, class_num, school_fk, date_of_birth):
    """Prideda studentą į clickhouse"""

    result = client.query("SELECT MAX(student_sk) FROM d_students")
    next_student_sk = result.result_set[0][0] + 1

    new_student = pd.DataFrame(
        {
            "student_sk": [next_student_sk],
            "first_name": [first_name],
            "last_name": [last_name],
            "class": [class_num],
            "school_fk": [school_fk],
            "date_of_birth": [pd.to_datetime(date_of_birth)],
        }
    )

    client.insert_df("d_students", new_student)
    return next_student_sk


def remove_student(client, student_sk):
    """Ištrina studentą iš clickhouse"""

    client.command(f"ALTER TABLE d_students DELETE WHERE student_sk = {student_sk}")


if __name__ == "__main__":
    client = get_clickhouse_client()

    student_id = add_student(
        client=client,
        first_name="desimtokas",
        last_name="desimtokas",
        class_num=10,
        school_fk=1,
        date_of_birth="2011-11-11",
    )

    # remove_student(client, student_id)
