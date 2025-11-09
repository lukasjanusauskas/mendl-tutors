import os
from dotenv import load_dotenv
load_dotenv()

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

def get_cassandra_session():
    cloud_config = {
        'secure_connect_bundle': 'secure-connect-mendltutors.zip'
    }

    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("SECRET")

    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("NO CLIENT ID OR SECRET")

    auth_provider = PlainTextAuthProvider(CLIENT_ID, CLIENT_SECRET)
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    session = cluster.connect()

    return session

if __name__ == "__main__":
    session = get_cassandra_session()

    source_table = 'by_sender2'
    target_table = 'by_sender'

    select_query = f'SELECT sender_role, sender_id, sent_at, message_id, message_text, student_id, tutor_id FROM messages.{source_table};'

    rows = session.execute(select_query)

    # Insert data row-by-row into target table
    insert_query = f'''
    INSERT INTO messages.{target_table} (sender_role, sender_id, sent_at, message_id, message_text, student_id, tutor_id)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    '''

    prepared = session.prepare(insert_query)

    for row in rows:
        session.execute(prepared, (row.sender_role, row.sender_id, row.sent_at, row.message_id, row.message_text, row.student_id, row.tutor_id))

    print(f"Copied {rows._current_rows} rows from {source_table} to {target_table}")
