"""
Kaip veikia:

1. Paimam studentus ir korepetitorius is mongo.
2. Paimam mokyklas is Neo4j.
3. Sukuriam siem trims po dimensine lentele, taip pat subjects sukuriam dimensine lentele.
4. Is Neo4j ir mongo kolekciju review ir lesson sukuriam faktu lentele.
"""

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


class DataWarehouseInitializer:

    def __init__(self):
        self.client = clickhouse_connect.get_client(
            host=HOST,
            user=USERNAME,
            password=PASSWORD,
            secure=True
        )

        self.neo4j_driver = get_neo4j_driver()
        self.mongo_driver = get_db()

    def get_all_schools(self):
        """ Surenka mokyklas ir sukuria jiems dimensine lentele. """

        query = """
        MATCH (sch:School)
        RETURN sch.name AS name,
               sch.nationality AS nationality;
        """

        # Get all students and their schools
        with self.neo4j_driver.session() as session:
            results = session.run(query)
            schools = [record.data() for record in results]

        assert len(schools) > 0, "Nesurinkta mokyklu"

        self.dim_schools = []
        for ix, school in enumerate(schools):
            self.dim_schools.append({
                'school_sk': ix + 1,
                'name': school['name'],
                'nationality': school['nationality'],
            })
    
    def get_student_school(self, student: dict):

        assert hasattr(self, "dim_schools"), "Schools have not been defined yet"

        query = f"""
        MATCH (s:Student {{first_name: "{student['first_name']}", last_name: "{student['last_name']}"}})
        MATCH (s:Student)-[:ATTENDS]->(sch:School)
        RETURN
            sch.name AS name,
            sch.nationality AS nationality;
        """

        with self.neo4j_driver.session() as session:
            results = session.run(query)
            results = list(results)

            if len(results) == 0:
                return 0

            else:
                school = results[0].data()

        # Get the key
        for school_dim_data in self.dim_schools:
            if school_dim_data['name'] != school['name']:
                continue

            else:
                return school_dim_data['school_sk']

        # Jeigu nera mokyklos - 0, nes, kai mokykla nustatyta jos sk >= 1
        return 0
        
    def get_all_students(self):
        """ Surenka studentus ir sukuria jiems dimensine lentele. """

        self.dim_students = []
        student_collection = self.mongo_driver['student']

        for ix, student in enumerate( student_collection.find({}) ):
            self.dim_students.append({
                'student_sk': ix + 1,
                'first_name': student['first_name'],
                'last_name': student['last_name'],
                'date_of_birth': student['date_of_birth'],
                'class': student['class'],
                'school_fk': self.get_student_school(student)
            })

    def get_all_tutors(self):
        """ Surenka korpetitorius ir sukuria jiems dimensine lentele. """

        self.dim_tutors = []
        tutor_collection = self.mongo_driver['tutor']

        for ix, tutor in enumerate( tutor_collection.find({})):
            self.dim_tutors.append({
                'tutor_sk': ix + 1,
                'first_name': tutor['first_name'],
                'last_name': tutor['last_name'],
                'date_of_birth': tutor['date_of_birth']
            })

    def get_student_key(self, student):
        for student_row in self.dim_students:
            if (student_row['first_name'] == student['first_name'] and
                student_row['last_name'] == student['last_name']):

                return student_row['student_sk']

        else:
            raise ValueError(f'Student {student} cannot be found in dim_students')

    def get_tutor_key(self, tutor):
        for tutor_row in self.dim_tutors:
            if (tutor_row['first_name'] == tutor['first_name'] and
                tutor_row['last_name'] == tutor['last_name']):

                return tutor_row['tutor_sk']

        else:
            raise ValueError(f'Tutor {tutor} cannot be found in dim_students')

    def get_total_lessons(
        self,
        student_data: dict,
        tutor_data: dict,
        subject: str,
    ):
        lesson_collection = self.mongo_driver['lesson']
        total_lesson_aggregation = lesson_collection.aggregate([
            # Surandam mokinio rasytus atsiliepimus korepetitoriui
            {
                "$match": {
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
            {"$count": "lesson_count"}
        ])

        try:
            agg_doc = next(total_lesson_aggregation)
            return agg_doc['lesson_count']

        except StopIteration:
            return 0  # jei nėra įvertintų atsiliepimų

    def get_avg_rating(
        self,
        student_data,
        tutor_data
    ):
        review_collection = self.mongo_driver['review']
        avg_rating_aggregation = review_collection.aggregate([
            # Surandam mokinio rasytus atsiliepimus korepetitoriui
            {
                "$match": {
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

    def make_fact_table(self):
        self.fact_table = []
        self.dim_subjects_dict: dict = {}

        query = """
        MATCH (s:Student)
        OPTIONAL MATCH (t:Tutor)-[st_conn:TEACHES]->(s:Student)
        RETURN s.first_name AS student_first_name, 
            s.last_name AS student_last_name, 
            s.class_num AS class,
            t.first_name AS tutor_first_name,
            t.last_name AS tutor_last_name,
            st_conn.subjects AS subjects
        """

        with self.neo4j_driver.session() as session:
            results = session.run(query)
            results = list(results)

        for student_tutor_pair in results:

            # Jei dalykai nenurodyti - praleidziam
            if student_tutor_pair['subjects'] is None:
                continue

            for subject in student_tutor_pair['subjects']:

                if subject in self.dim_subjects_dict:
                    subject_fk = self.dim_subjects_dict[subject]
                else:
                    subject_fk = len(self.dim_subjects_dict)
                    self.dim_subjects_dict[subject] = subject_fk

                student_data = {
                    'first_name': student_tutor_pair['student_first_name'],
                    'last_name': student_tutor_pair['student_last_name'],
                }
                tutor_data = {
                    'first_name': student_tutor_pair['tutor_first_name'],
                    'last_name': student_tutor_pair['tutor_last_name'],
                }

                self.fact_table.append({
                    'student_fk': self.get_student_key(student_data),
                    'tutor_fk': self.get_tutor_key(tutor_data),
                    'subject_fk': subject_fk,
                    'studied_with_tutor_from': datetime.now(),
                    'studied_with_tutor_to': None,
                    'total_lessons': self.get_total_lessons(student_data, tutor_data, subject),
                    'rating': self.get_avg_rating(student_data, tutor_data),
                })

    def get_subjects_dim_table(self):
        self.dim_subjects = []

        for subject_name, surogate_key in self.dim_subjects_dict.items():
            self.dim_subjects.append({
                'subject_sk': surogate_key,
                'name': subject_name
            })

    
    def fill_dw_data_in_clickhouse(self):
        # Save fact table
        self.client.insert_df(
            'f_student_tutor_stat',
            pd.DataFrame(self.fact_table)
        )

        # Save dimension tables
        self.dim_tutors = pd.DataFrame(self.dim_tutors)
        self.dim_tutors['date_of_birth'] = pd.to_datetime(self.dim_tutors['date_of_birth'], errors='coerce')
        self.client.insert_df('dim_tutors', self.dim_tutors)

        self.client.insert_df(
            'dim_subjects', 
            pd.DataFrame(self.dim_subjects) 
        )
        self.client.insert_df(
            'dim_schools',
            pd.DataFrame(self.dim_schools)
        )

        self.dim_students = pd.DataFrame(self.dim_students)
        self.dim_students['date_of_birth'] = pd.to_datetime(self.dim_students['date_of_birth'], errors='coerce')
        self.client.insert_df('dim_students', self.dim_students)



    def main(self):
        self.get_all_schools()
        self.get_all_students()
        self.get_all_tutors()
        self.make_fact_table()
        self.get_subjects_dim_table()

        print(*self.dim_schools, sep='\n')
        print(*self.dim_students, sep='\n')
        print(*self.dim_tutors, sep='\n')
        print(*self.dim_subjects, sep='\n')
        print(*self.fact_table, sep='\n')

        self.fill_dw_data_in_clickhouse()


if __name__ == '__main__':
    dw_init = DataWarehouseInitializer()
    dw_init.main()