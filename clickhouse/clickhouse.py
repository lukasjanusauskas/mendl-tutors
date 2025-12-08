from clickhouse.clickhouse_config import (
    USERNAME,
    PASSWORD,
    HOST,
)

import clickhouse_connect
from neo4j_db.neo4j_client import get_driver as get_neo4j_driver
import pandas as pd
from datetime import date, datetime
from api.student import get_students_by_name
from api.tutor import get_tutors_by_name
from api.connection import get_db

FACT_TABLE_COLUMNS = [
    'student_fk', 
    'tutor_fk', 
    'subject_fk', 
    'studied_with_tutor_from',
    'studied_with_tutor_to',
    'total_lessons', 
    'rating', 
]


def get_students_schools_neo4j(neo4j_driver):

    query = """
    MATCH (s:Student)
    OPTIONAL MATCH (s:Student)-[:ATTENDS]->(sch:School)
    OPTIONAL MATCH (t:Tutor)-[st_conn:TEACHES]->(s:Student)
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


def form_student_data(data_row, ix, student_collection, school_ix):
    output = {
        'student_sk': ix,
        'first_name': data_row['student_first_name'],
        'last_name': data_row['student_last_name'],
        'class': data_row['class'],
        'school_fk': school_ix,
    }

    student_mongo = get_students_by_name(
        student_collection,
        output['first_name'],
        output['last_name']
    )[0]

    output['date_of_birth'] = student_mongo['date_of_birth']
        
    return output


def form_tutor_data(data_row, ix, tutor_collection):
    output = {
        'tutor_sk': ix,
        'first_name': data_row['tutor_first_name'],
        'last_name': data_row['tutor_last_name'],
    }

    tutor_mongo = get_tutors_by_name(
        tutor_collection,
        output['first_name'],
        output['last_name']
    )[0]

    output['date_of_birth'] = tutor_mongo['date_of_birth']

    return output


def form_school_data(data_row, ix):
    output = {
        'school_sk': ix,
        'name': data_row['school_name'],
        'nationality': data_row['school_nationality'],
    }

    return output


def get_dimension_table(dimension_data: dict):
    raw_rows = dimension_data.values()
    return pd.DataFrame(raw_rows)


def get_fact_table(
    fact_table_rows: list[tuple],
    columns: list[str] = FACT_TABLE_COLUMNS
):
    return pd.DataFrame(
        fact_table_rows,
        columns=columns
    )


def parse_all_data(
    data,
    student_collection,
    tutor_collection
):

    # For storing fact table
    fact_table_rows = []

    # For storing dimension table
    students = {}
    tutors = {}
    schools = {}
    subjects = {}

    for data_row in data:

        # Korepetitoriaus raktas tutors dict
        tutor_key = (
            data_row['tutor_first_name'], 
            data_row['tutor_last_name']
        )
        if tutor_key[0] is None:
            if tutor_key in tutors:
                tutor_ix = tutors[tutor_key]['tutor_sk']

            else:
                tutors[tutor_key] = {
                    'tutor_sk': len(tutors),
                    'first_name': '',
                    'last_name': '',
                    'date_of_birth': None
                }
                tutor_ix = len(tutors) - 1

        elif tutor_key not in tutors:
            tutors[tutor_key] = form_tutor_data(data_row, len(tutors), tutor_collection)
            tutor_ix = len(tutors) - 1

        else:
            tutor_ix = tutors[tutor_key]['tutor_sk']

        # Korepetitoriaus raktas tutors dict
        school_key = data_row['school_name']
        if school_key not in schools:
            schools[school_key] = form_school_data(data_row, len(schools))
            school_ix = len(schools) - 1

        else:
            school_ix = schools[school_key]['school_sk']

        # Studento raktas students dictionary
        student_key = (
            data_row['student_first_name'], 
            data_row['student_last_name']
        )
        if student_key[0] is None:
            if student_key in students: 
                student_ix = students[student_key]['student_sk']
            else:
                students[student_key] = {
                    'student_sk': len(students),
                    'first_name': '',
                    'last_name': '',
                    'class': 0,
                    'school_fk': None,
                    'valid_from': None,
                    'valid_to': None,
                    'date_of_birth': None
                }
                student_ix = len(students) - 1

        elif student_key not in students:
            students[student_key] = form_student_data(
                data_row, 
                len(students), 
                student_collection,
                school_ix
            )
            student_ix = len(students) - 1

        else:
            student_ix = students[student_key]['student_sk']

        # Iterate over subjects since one tutor can teach multiple subjects
        # If there are no subjects - subject_ix is None
        if data_row['subjects'] is None:
            if data_row['subjects'] in subjects:
                subject_ix = subjects[data_row['subjects']]['subject_sk']
            else:
                subjects[None] = {
                    'subject_sk': len(subjects),
                    'name': ''
                }
                subject_ix = len(subjects) - 1

            fact_table_rows.append((
                student_ix,
                tutor_ix,
                subject_ix,
                datetime.now(),
                None,
                0,
                None,
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
                    subject_ix = len(subjects) - 1

                fact_table_rows.append((
                    student_ix,
                    tutor_ix,
                    subject_ix,
                    datetime.now(),
                    None,
                    0,
                    None,
                ))

    return (
        fact_table_rows,
        students,
        tutors,
        schools,
        subjects
    )


def get_total_lessons(
    student_data: dict,
    tutor_data: dict,
    subject: str,
    lesson_collection
):
    total_lesson_aggregation = lesson_collection.aggregate([
        # Surandam mokinio rasytus atsiliepimus korepetitoriui
        {
            "$match":{
                "students.first_name": student_data['first_name'],
                "students.last_name": student_data['last_name'],
                "tutor.first_name": tutor_data['first_name'],
                "tutor.last_name": tutor_data['last_name'],
                
                # Surandam neistrintas pamokas
                "type": {"$ne": "DELETED"},
                "subject": subject
            }
        },
        # Apskaiciuoti
        { "$count": "lesson_count" }
    ])

    try:
        agg_doc = next(total_lesson_aggregation)
        return agg_doc['lesson_count']

    except StopIteration:
        return None  # jei nėra įvertintų atsiliepimų


def get_avg_rating(
    student_data,
    tutor_data,
    review_collection
):
    avg_rating_aggregation = review_collection.aggregate([
        # Surandam mokinio rasytus atsiliepimus korepetitoriui
        {
            "$match":{
                "student.first_name": student_data['first_name'],
                "student.last_name": student_data['last_name'],
                "tutor.first_name": tutor_data['first_name'],
                "tutor.last_name": tutor_data['last_name'],
                "for_tutor": True
            }
        },

        # Apskaiciuojame vidurki
        {
            "$group": {
                "_id": None,
                "average_rating": {
                    "$avg": "$rating"
                }
            }
        }
    ])

    try:
        agg_doc = next(avg_rating_aggregation)
        return agg_doc['average_rating']

    except StopIteration:
        return None  # jei nėra įvertintų atsiliepimų


def fill_dw_data_in_clickhouse(
    dw_client,
    f_student_tutor_statistcs,
    d_student,
    d_tutor,
    d_school,
    d_subjects
):

    # Save fact table
    dw_client.insert_df(
        'f_student_tutor_stats',
        f_student_tutor_statistcs
    )

    # Save dimension tables
    d_tutor['date_of_birth'] = pd.to_datetime( d_tutor['date_of_birth'], errors='coerce')
    dw_client.insert_df('d_tutors', d_tutor)
    dw_client.insert_df('d_subjects', d_subjects)
    dw_client.insert_df('d_schools', d_school)

    d_student['date_of_birth'] = pd.to_datetime( d_student['date_of_birth'], errors='coerce')
    dw_client.insert_df('d_students', d_student)


def fill_dw_from_zero(
    dw_client,
    neo4j_driver,
    mongo_driver
):
    # Get all students, their schools and tutors
    data = get_students_schools_neo4j(neo4j_driver)
    student_collection = mongo_driver['student']
    tutor_collection = mongo_driver['tutor']
    review_collection = mongo_driver['review']
    lesson_collection = mongo_driver['lesson']

    # Form the fact and dimension tables
    fact_table_rows, students, tutors, schools, subjects = parse_all_data(
        data, student_collection, tutor_collection
    )

    f_student_tutor_statistcs = get_fact_table(fact_table_rows)
    d_student = get_dimension_table(students)
    d_tutor = get_dimension_table(tutors)
    d_school = get_dimension_table(schools)
    d_subjects = get_dimension_table(subjects)

    # Get the number of lessons and the rating
    ratings = []
    for _, data_row in f_student_tutor_statistcs.iterrows():
        student_data = d_student.iloc[data_row['student_fk'], :]
        tutor_data = d_tutor.iloc[data_row['tutor_fk'], :]

        ratings.append( get_avg_rating(
            student_data,
            tutor_data,
            review_collection
        ) )

    # Get lesson counts
    lesson_counts = []
    for _, data_row in f_student_tutor_statistcs.iterrows():
        student_data = d_student.iloc[data_row['student_fk'], :]
        tutor_data = d_tutor.iloc[data_row['tutor_fk'], :]
        subject = d_subjects.iloc[data_row['subject_fk'], 1]

        lesson_counts.append( get_total_lessons(
            student_data,
            tutor_data,
            subject,
            lesson_collection
        ) )

    f_student_tutor_statistcs['total_lessons'] = lesson_counts
    f_student_tutor_statistcs['rating'] = ratings

    # Push all data to SQL
    fill_dw_data_in_clickhouse(
        dw_client,
        f_student_tutor_statistcs,
        d_student,
        d_tutor,
        d_school,
        d_subjects
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
    mongo_driver = get_db()

    fill_dw_from_zero(client, neo4j_driver, mongo_driver)

