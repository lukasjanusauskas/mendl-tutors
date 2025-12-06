from clickhouse.clickhouse_config import (
    USERNAME,
    PASSWORD,
    HOST,
)

import clickhouse_connect
from neo4j_db.neo4j_client import get_driver as get_neo4j_driver
import pandas as pd
from api.student import get_students_by_name
from api.connection import get_db


def get_students_schools_neo4j(neo4j_driver):

    query = """
    OPTIONAL MATCH (s:Student)-[:ATTENDS]->(sch:School)
    MATCH (t:Tutor)-[st_conn:TEACHES]->(s:Student)
    RETURN s.first_name AS student_first_name, 
        s.last_name AS student_last_name, 
        s.class_num AS class,
        t.first_name AS tutor_first_name,
        t.last_name AS tutor_last_name,
        st_conn.subjects AS subjects,
        sch.name AS school_name,
        sch.nationality AS school_nationality;
    """

    # Get all students and their schools
    with neo4j_driver.session() as session:
        results = session.run(query)
        return [record.data() for record in results]



def form_student_data(data_row, ix, student_collection):
    output = {
        'student_sk': ix,
        'first_name': data_row['student_first_name'],
        'last_name': data_row['student_last_name'],
        'class': data_row['class']
    }

    student_mongo = get_students_by_name(
        student_collection,
        output['first_name'],
        output['last_name']
    )[0]

    output['date_of_birth'] = student_mongo['date_of_birth']
        
    return output
        

def form_tutor_data(data_row, ix):
    output = {
        'tutor_sk': ix,
        'first_name': data_row['tutor_first_name'],
        'last_name': data_row['tutor_last_name'],
        'date_of_birth': None
    }

    return output


def form_school_data(data_row, ix):
    output = {
        'school_sk': ix,
        'name': data_row['school_name'],
        'nationality': data_row['school_nationality'],
        # TODO: figure something out
        'start_date': None,
        'end_date': None
    }

    return output


def get_dimension_table(dimension_data: dict):
    raw_rows = dimension_data.values()
    return pd.DataFrame(raw_rows)


def get_fact_table(
    fact_table_rows: list[tuple],
    columns: list[str]
):
    return pd.DataFrame(
        fact_table_rows,
        columns=columns
    )


def parse_all_data(
    data,
    student_collection
):

    # For storing fact table
    fact_table_rows = []

    # For storing dimension table
    students = {}
    tutors = {}
    schools = {}
    subjects = {}

    for data_row in data:

        # Studento raktas students dictionary
        student_key = (
            data_row['student_first_name'], 
            data_row['student_last_name']
        )
        if student_key not in students:
            students[student_key] = form_student_data(data_row, len(students), student_collection)
            student_ix = len(students)

        else:
            student_ix = students[student_key]['student_sk']

        # Korepetitoriaus raktas tutors dict
        tutor_key = (
            data_row['tutor_first_name'], 
            data_row['tutor_last_name']
        )
        if tutor_key not in tutors:
            tutors[tutor_key] = form_tutor_data(data_row, len(tutors))
            tutor_ix = len(tutors)

        else:
            tutor_ix = tutors[tutor_key]['tutor_sk']

        # Korepetitoriaus raktas tutors dict
        school_key = data_row['school_name']
        if school_key not in schools:
            schools[school_key] = form_school_data(data_row, len(schools))
            school_ix = len(schools)

        else:
            school_ix = schools[school_key]['school_sk']


        # Iterate over subjects since one tutor can teach multiple subjects
        # If there are no subjects - subject_ix is None
        if data_row['subjects'] is None:
            fact_table_rows.append((
                student_ix,
                tutor_ix,
                school_ix,
                None,
                0,
                None
            ))

        # Else go over each subject and create a new row for each
        else:
            for subject in data_row['subjects']:

                if subject in subjects:
                    subject_ix = subjects[subject]['subject_sk']
                else:
                    subjects[subject] = {
                        'subject_sk': len(subjects),
                        'name': subject
                    }
                    subject_ix = len(subjects)

                fact_table_rows.append((
                    student_ix,
                    tutor_ix,
                    school_ix,
                    subject_ix,
                    0,
                    None
                ))

    return (
        fact_table_rows,
        students,
        tutors,
        schools,
        subjects
    )


if __name__ == '__main__':
    client = clickhouse_connect.get_client(
        host=HOST,
        user=USERNAME,
        password=PASSWORD,
        secure=True
    )

    # print("Result:", client.query("SELECT 1").result_set[0][0])
    neo4j_driver = get_neo4j_driver()
    data = get_students_schools_neo4j(neo4j_driver)

    mongo_driver = get_db()
    student_collection = mongo_driver['student']

    for row in parse_all_data(data, student_collection):
        print(row)
