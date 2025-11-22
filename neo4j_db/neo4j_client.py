import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, Neo4jDriver

# Load environment variables from .env file
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")
AURA_INSTANCEID = os.getenv("AURA_INSTANCEID")

def get_driver() -> Neo4jDriver:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    return driver

def run_query(driver, query):
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query)
        return [record.data() for record in result]

if __name__ == "__main__":
    driver = get_driver()

    print(f"Connecting to Aura instance: {AURA_INSTANCEID}")
    query = "MATCH (n) RETURN n LIMIT 5"
    records = run_query(driver, query)

    for record in records:
        print(record)

    driver.close()