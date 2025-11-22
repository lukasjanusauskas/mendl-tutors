from neo4j_db.neo4j_client import get_driver
from api.connection import get_db
from api.student import get_all_students
from api.tutor import get_all_tutors

import os
from dotenv import load_dotenv
load_dotenv()

NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

def create_student_node(driver, student: dict):
    query = f"""
    CREATE (student:Student {{first_name: '{student['first_name']}', 
                              last_name: '{student['last_name']}',
                              class_num: {student['class']}, 
                              subjects: {student['subjects']}}})
    """

    result = driver.execute_query(query,
        database_=NEO4J_DATABASE)


def create_tutor_node(driver, tutor: dict):

    if 'rating' in tutor:
        query = f"""
        CREATE (tutor:Tutor {{first_name: '{tutor['first_name']}', 
                            last_name: '{tutor['last_name']}',
                            rating: {tutor['rating']}, 
                            subjects: {tutor['subjects']}}})
        """

    elif len(tutor['subjects']) > 0:

        if isinstance( tutor['subjects'][0], dict):
            subjects = [subj['subject'] for subj in tutor['subjects']]
            query = f"""
            CREATE (tutor:Tutor {{first_name: '{tutor['first_name']}', 
                                last_name: '{tutor['last_name']}',
                                subjects: {subjects}}})
            """
        
        else:
            query = f"""
            CREATE (tutor:Tutor {{first_name: '{tutor['first_name']}', 
                                last_name: '{tutor['last_name']}',
                                subjects: {tutor['subjects']}}})
            """

    else:
        query = f"""
        CREATE (tutor:Tutor {{first_name: '{tutor['first_name']}', 
                            last_name: '{tutor['last_name']}',
                            subjects: {tutor['subjects']}}})
        """
    
    result = driver.execute_query(query,
        database_=NEO4J_DATABASE)


def create_relationships(neo4j_driver, tutor: dict):

    subject_lists: dict = {}

    for student_subject in tutor['students_subjects']:

        first = student_subject['student']['first_name']
        last = student_subject['student']['last_name']

        if 'subject' not in student_subject:
            continue

        if (first,last) not in subject_lists:
            subject_lists[(first, last)] = [student_subject['subject']]
        else:
            subject_lists[(first, last)].append(
                student_subject['subject']
            )

    for (first_name, last_name), subjects in subject_lists.items():

        query = f"""
        MATCH (t:Tutor {{first_name: "{tutor['first_name']}", last_name: "{tutor['last_name']}"}}), 
            (s:Student {{first_name: "{first_name}", last_name: "{last_name}"}})

        CREATE (t)-[:TEACHES {{subjects: {subjects}}}]->(s)
        """

        result = neo4j_driver.execute_query(query,
            database_=NEO4J_DATABASE)


def generate_school(neo4j_driver, school: dict):
    query = f"""
    CREATE (school:School {{name: '{school['school_name']}', 
                            country: '{school['country']}',
                            nationality: '{school['nationality']}' }})
    """

    result = neo4j_driver.execute_query(query,
        database_=NEO4J_DATABASE)


def main():
    neo4j_driver = get_driver()
    mongo_driver = get_db()

    # Migrate students ###################

    # student_collection = mongo_driver['student']

    # for student in get_all_students(student_collection):
    #     create_student_node(neo4j_driver, student)
    #     print('-' * 50)


    # Migrate tutors ##########################3

    # tutor_collection = mongo_driver['tutor']

    # for tutor in get_all_tutors(tutor_collection):
    #     create_tutor_node(neo4j_driver, tutor)
    #     print('-' * 50)


    # Create relationships #####################3

    # tutor_collection = mongo_driver['tutor']

    # for tutor in get_all_tutors(tutor_collection):
    #     create_relationships(neo4j_driver, tutor)

    schools = [
        {'school_name': 'A gimnazija', 'country': 'LIT', 'nationality': 'lithuanian'},
        {'school_name': 'R gimnazija', 'country': 'LIT', 'nationality': 'russian'},
        {'school_name': 'L vidusskola', 'country': 'LAT', 'nationality': 'latvian'},
    ]

    for school in schools:
        generate_school(neo4j_driver, school)



if __name__ == "__main__":
    main()