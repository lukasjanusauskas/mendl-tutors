from neo4j_db.neo4j_client import get_driver, NEO4J_DATABASE


def get_schools(driver):
    query = """
    MATCH (school:School)
    RETURN school.name AS school_name
    ORDER BY school.name
    """

    schools = []
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query)
        for record in result:
            data = record.data()
            schools.append(str(data.get("school_name", "")))

    return schools


def get_tutors_by_school(driver, school_name):
    query = """
    MATCH (t:Tutor)-[:TEACHES]->(s:Student)
    MATCH (s)-[:ATTENDS]->(school:School {name: $school_name})
    RETURN DISTINCT t.first_name AS first_name,
                    t.last_name AS last_name,
                    school.name AS school_name
    """

    tutors = []
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query, school_name=school_name)
        for record in result:
            data = record.data()
            tutors.append(
                {
                    "first_name": str(data.get("first_name", "")),
                    "last_name": str(data.get("last_name", "")),
                    "school_name": str(data.get("school_name", "")),
                }
            )

    return tutors


if __name__ == "__main__":
    # python -m api.neo4j
    import os

    AURA_INSTANCEID = os.getenv("AURA_INSTANCEID")
    driver = get_driver()
    school_name = "C mokykla"

    schools = get_schools(driver)
    print(schools)

    tutors = get_tutors_by_school(driver, school_name)
    print(tutors)
    driver.close()
