from cassandra.cluster import Session
import time
from datetime import datetime, timezone
from uuid import uuid4

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

    # Convert given time to UTC
    utc_time = datetime.now(timezone.utc)
    
    # Generate a new UUID for the id column
    payment_id = uuid4()
    
    # Prepare the CQL insert statements with placeholders FOR EACH TABLE
    tables = ['tutor_by_student_time', 'student_by_tutor_time', 'time_by_amount']
    cql_inserts = ["""INSERT INTO payments.""" + table + """ (
            id, tutor_id, student_id, payment, time_payment, is_complete
        ) VALUES ({}, '{}', '{}', {}, '{}', {})
        """
        for table in tables]

    # Bind values to parameters
    params = (payment_id, tutor_id, student_id, payment, utc_time, True)
    
    # Execute the query
    for cql_insert in cql_inserts:
        cassandra_session.execute(cql_insert, params)

def read_payments_to_tutor():

    # Read payments from query

    # Convert to local time

    pass

def read_payments_from_student():
    pass