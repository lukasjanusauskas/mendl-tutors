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


def send_friend_request(
    driver,
    from_student_first_name,
    from_student_last_name,
    to_student_first_name,
    to_student_last_name,
):

    if (
        from_student_first_name == to_student_first_name
        and from_student_last_name == to_student_last_name
    ):
        return "Cannot send request to yourself."

    query = """
    MATCH (a:Student {first_name: $from_student_first_name, last_name: $from_student_last_name})
    MATCH (b:Student {first_name: $to_student_first_name, last_name: $to_student_last_name})

    OPTIONAL MATCH (a)-[f:FRIENDS_WITH]-(b)
    OPTIONAL MATCH (a)-[existing_req:REQUESTS_FRIENDSHIP]->(b)
    OPTIONAL MATCH (b)-[reverse_req:REQUESTS_FRIENDSHIP]->(a)
    LIMIT 1

    RETURN 
        CASE 
            WHEN f IS NOT NULL THEN 'ALREADY_FRIENDS'
            WHEN existing_req IS NOT NULL THEN 'REQUEST_ALREADY_SENT'
            WHEN reverse_req IS NOT NULL THEN 'REVERSE_REQUEST_PENDING'
            ELSE 'PROCEED_WITH_REQUEST'
        END AS Status
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            query,
            from_student_first_name=from_student_first_name,
            from_student_last_name=from_student_last_name,
            to_student_first_name=to_student_first_name,
            to_student_last_name=to_student_last_name,
        ).single()

        if not result:
            return "Studentas nerastas."

        status = result.data().get("Status")

        if status == "ALREADY_FRIENDS":
            return "Tokia draugystė jau egzistuoja."
        elif status == "REQUEST_ALREADY_SENT":
            return "Draugystės prašymas jau išsiųstas."
        elif status == "REVERSE_REQUEST_PENDING":
            accept_friend_request(
                driver,
                from_student_first_name=to_student_first_name,
                from_student_last_name=to_student_last_name,
                to_student_first_name=from_student_first_name,
                to_student_last_name=from_student_last_name,
            )
            return "Kadangi šis studentas jau išsiuntė jums draugystės prašymą, draugystė buvo automatiškai patvirtinta."
        else:
            query = """
            MATCH (sender:Student {first_name: $from_student_first_name, last_name: $from_student_last_name})
            MATCH (receiver:Student {first_name: $to_student_first_name, last_name: $to_student_last_name})
            MERGE (sender)-[:REQUESTS_FRIENDSHIP]->(receiver)
            """
            session.run(
                query,
                from_student_first_name=from_student_first_name,
                from_student_last_name=from_student_last_name,
                to_student_first_name=to_student_first_name,
                to_student_last_name=to_student_last_name,
            )
            return "Draugystės prašymas išsiųstas."


def accept_friend_request(
    driver,
    from_student_first_name,
    from_student_last_name,
    to_student_first_name,
    to_student_last_name,
):
    query = """
    MATCH (sender:Student {first_name: $from_student_first_name, last_name: $from_student_last_name})
    MATCH (receiver:Student {first_name: $to_student_first_name, last_name: $to_student_last_name})
    MATCH (sender)-[r:REQUESTS_FRIENDSHIP]->(receiver)
    DELETE r
    MERGE (sender)-[:FRIENDS_WITH]->(receiver)
    MERGE (receiver)-[:FRIENDS_WITH]->(sender)
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            query,
            from_student_first_name=from_student_first_name,
            from_student_last_name=from_student_last_name,
            to_student_first_name=to_student_first_name,
            to_student_last_name=to_student_last_name,
        )


def decline_friend_request(
    driver,
    from_student_first_name,
    from_student_last_name,
    to_student_first_name,
    to_student_last_name,
):
    query = """
    MATCH (sender:Student {first_name: $from_student_first_name, last_name: $from_student_last_name})
    MATCH (receiver:Student {first_name: $to_student_first_name, last_name: $to_student_last_name})
    MATCH (sender)-[r:REQUESTS_FRIENDSHIP]->(receiver)
    DELETE r
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            query,
            from_student_first_name=from_student_first_name,
            from_student_last_name=from_student_last_name,
            to_student_first_name=to_student_first_name,
            to_student_last_name=to_student_last_name,
        )


def get_pending_friend_requests(driver, student_first_name, student_last_name):
    query = """
    MATCH (sender:Student)-[:REQUESTS_FRIENDSHIP]->(receiver:Student {first_name: $student_first_name, last_name: $student_last_name})
    RETURN sender.first_name AS first_name, sender.last_name AS last_name
    """

    requests = []
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            query,
            student_first_name=student_first_name,
            student_last_name=student_last_name,
        )
        for record in result:
            data = record.data()
            requests.append(
                {
                    "first_name": str(data.get("first_name", "")),
                    "last_name": str(data.get("last_name", "")),
                }
            )

    return requests


def get_friends(driver, student_first_name, student_last_name):
    query = """
    MATCH (student:Student {first_name: $student_first_name, last_name: $student_last_name})-[:FRIENDS_WITH]-(friend:Student)
    RETURN DISTINCT friend.first_name AS first_name, friend.last_name AS last_name
    """

    friends = []
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            query,
            student_first_name=student_first_name,
            student_last_name=student_last_name,
        )
        for record in result:
            data = record.data()
            friends.append(
                {
                    "first_name": str(data.get("first_name", "")),
                    "last_name": str(data.get("last_name", "")),
                }
            )

    return friends


def remove_friend(
    driver,
    student1_first_name,
    student1_last_name,
    student2_first_name,
    student2_last_name,
):
    query = """
    MATCH (a:Student {first_name: $student1_first_name, last_name: $student1_last_name})
    MATCH (b:Student {first_name: $student2_first_name, last_name: $student2_last_name})
    MATCH (a)-[f:FRIENDS_WITH]-(b)
    DELETE f
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            query,
            student1_first_name=student1_first_name,
            student1_last_name=student1_last_name,
            student2_first_name=student2_first_name,
            student2_last_name=student2_last_name,
        )


if __name__ == "__main__":
    # python -m api.neo4j
    import os

    AURA_INSTANCEID = os.getenv("AURA_INSTANCEID")
    driver = get_driver()
    school_name = "C mokykla"

    schools = get_schools(driver)
    print("Visos mokyklos: ", schools)

    tutors = get_tutors_by_school(driver, school_name)
    print(f"Korepetitoriai, kurie moko {school_name} mokinius: {tutors}")

    friend_req = send_friend_request(
        driver, "Zigmas", "Zigmaitis", "Petras", "Petraitis"
    )
    print("Zigmo Zigmaičio draugystės prašymas Petrui Petraičiui:", friend_req)

    friend_req = send_friend_request(driver, "Zigmas", "Zigmaitis", "auth", "testas")
    print("Zigmo Zigmaičio draugystės prašymas auth testui:", friend_req)

    pending = get_pending_friend_requests(driver, "auth", "testas")
    print(f"auth testui išsiųsti draugystės prašymai: {pending}")

    friends = get_friends(driver, "Zigmas", "Zigmaitis")
    print(f"Zigmo Zigmaičio draugai: {friends}")

    decline_friend_request(driver, "Zigmas", "Zigmaitis", "auth", "testas")

    driver.close()
