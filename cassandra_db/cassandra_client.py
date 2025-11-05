
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