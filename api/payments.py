from cassandra_db.cassandra_client import get_cassandra_session
from cassandra.cluster import Session

import time
from datetime import datetime, timezone
from uuid import uuid4
from decimal import *
getcontext().prec = 3 # Nustato precision decimal tipui

from api.utils import get_student_name
from api.tutor import get_tutor_by_id
from api.connection import get_db

def create_payment(
    cassandra_session: Session,
    student_id: str,
    tutor_id: str,
    payment: float
):
    """
    Create a payment from student and tutor ids and payment.
    Time is converted to UTC.
    """
    
    # Importuojam cia, kad nebutu circular import
    from api.aggregates import invalidate_tutor_pay_cache, invalidate_student_pay_cache

    # Convert given time to UTC
    utc_time = datetime.now(timezone.utc)
    
    # Generate a new UUID for the id column
    payment_id = uuid4()
    
    # Prepare the CQL insert statements with placeholders FOR EACH TABLE
    tables = ['tutor_by_student_time', 'student_by_tutor_time', 'time_by_amount']
    cql_inserts = [f"""INSERT INTO payments.{table} (
            id, tutor_id, student_id, payment, time_payment, is_complete
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        for table in tables]

    # Bind values to parameters
    payment = Decimal(payment).quantize(Decimal('0.001'))
    params = (payment_id, tutor_id, student_id, payment, utc_time, True)
    
    # Execute the query
    for cql_insert in cql_inserts:
        cassandra_session.execute(cql_insert, params)

    # Invalidate cache
    invalidate_tutor_pay_cache(tutor_id)
    invalidate_student_pay_cache(student_id)


def read_payments_to_tutor(
    cassandra_session: Session,
    tutor_collection,
    tutor_id: str
):
    """
    Read all payments made to tutor, order by time and student_id by default.
    Converts from UTC to local time.
    """

    # Read payments from query
    query = f"""
    SELECT * FROM payments.tutor_by_student_time WHERE tutor_id = '{tutor_id}';
    """

    # Get the payments
    rows = cassandra_session.execute(query)

    if not rows:
        return []

    return_rows = []
    tutor = get_tutor_by_id(tutor_collection, tutor_id)
    for row in rows:
        # get student name from tutor info
        student_name = get_student_name(tutor['students_subjects'], row.student_id)

        # get payment info
        return_rows.append({
            'time_payment': row.time_payment,
            'payment': row.payment,
            'student': student_name
        })

    # Convert to local time
    return return_rows


def read_payments_from_student(
    cassandra_session: Session,
    tutor_collection,
    student_id: dict
): 
    """
    Read all payments made to tutor, order by time and student_id by default.
    Converts from UTC to local time.
    """

    # Read payments from query
    query = f"""
    SELECT * FROM payments.student_by_tutor_time WHERE student_id = '{student_id}';
    """

    # Get the payments
    rows = cassandra_session.execute(query)

    if not rows:
        return []

    return_rows = []

    for row in rows:
        # get student name from tutor info
        tutor = get_tutor_by_id(tutor_collection, row.tutor_id)

        # get payment info
        return_rows.append({
            'time_payment': row.time_payment,
            'payment': row.payment,
            'tutor': f"{tutor['first_name']} {tutor['last_name']}" 
        })

    # Convert to local time
    return return_rows


if __name__ == "__main__":
    
    session = get_cassandra_session()
    tutor_id = '6903c26c345e987b42e65ab7'
    student_id = '68e9005c9ad6add2ad36b361'

    db = get_db()
    tutor = get_tutor_by_id(db['tutor'], tutor_id)

    print( read_payments_from_student(session, db['tutor'], student_id) )