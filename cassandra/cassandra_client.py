from cassandra.cluster import Cluster
import os
from dotenv import load_dotenv
load_dotenv()

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

cloud_config= {
  'secure_connect_bundle': 'secure-connect-mendltutors.zip'
}

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("SECRET")

auth_provider = PlainTextAuthProvider(CLIENT_ID, CLIENT_SECRET)
cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
session = cluster.connect()

rows = session.execute("SELECT * FROM payments.by_id")
for row in rows:
  print(row)