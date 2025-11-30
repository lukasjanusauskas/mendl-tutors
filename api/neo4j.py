from neo4j_db.neo4j_client import get_driver, NEO4J_DATABASE


def get_schools(driver):
    """Grąžina visas mokyklas"""
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
    """Grąžina korepetitorius, kurie mokina tam tikros mokyklos mokinius"""
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
                }
            )

    return tutors

def create_student(driver, student_first_name, student_last_name, class_num=None):
    """Sukuria mokinį neo4j duomenų bazėje"""
    query = """
    MERGE (s:Student {first_name: $student_first_name, last_name: $student_last_name})
    ON CREATE SET s.class_num = $class_num
    RETURN s
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            query,
            student_first_name=student_first_name,
            student_last_name=student_last_name,
            class_num=class_num,
        )

def set_student_school(driver, student_first_name, student_last_name, school_name):
    """Prideda mokinį prie mokyklos"""
    query = """
    MATCH (s:Student {first_name: $student_first_name, last_name: $student_last_name})
    MATCH (school:School {name: $school_name})
    MERGE (s)-[:ATTENDS]->(school)
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            query,
            student_first_name=student_first_name,
            student_last_name=student_last_name,
            school_name=school_name,
        ) 

def set_student_tutor(driver, student_first_name, student_last_name, tutor_first_name, tutor_last_name):
    """Prideda mokinį prie korepetitoriaus"""
    query = """
    MATCH (s:Student {first_name: $student_first_name, last_name: $student_last_name})
    MATCH (t:Tutor {first_name: $tutor_first_name, last_name: $tutor_last_name})
    MERGE (t)-[:TEACHES]->(s)
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        session.run(
            query,
            student_first_name=student_first_name,
            student_last_name=student_last_name,
            tutor_first_name=tutor_first_name,
            tutor_last_name=tutor_last_name,
        ) 

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


def cancel_friend_request(
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


def get_sent_friend_requests(driver, student_first_name, student_last_name):
    query = """
    MATCH (sender:Student {first_name: $student_first_name, last_name: $student_last_name})-[:REQUESTS_FRIENDSHIP]->(receiver:Student)
    RETURN receiver.first_name AS first_name, receiver.last_name AS last_name
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


def get_subject_tutors_by_student_friends_path_length_to_that_tutor(
    driver, student_first_name, student_last_name, subject, max_path_length, existing_tutors
):
    """
    Grąžina korepetitorius draugų tinkle, kurie dar nėra priskirti studentui.
    existing_tutors: list of "FirstName LastName" korepetitorių, kuriuos studentas jau turi
    """
    friends = get_friends(driver, student_first_name, student_last_name)
    if not friends:
        return None

    query = f"""
    MATCH (student:Student {{first_name: $student_first_name, last_name: $student_last_name}})
    MATCH path = (student)-[:FRIENDS_WITH*1..{max_path_length}]-(friend:Student)-[teaches:TEACHES]-(tutor:Tutor)
    WHERE $subject IN tutor.subjects
      AND ALL(n IN nodes(path) WHERE single(x IN nodes(path) WHERE x = n))
      AND NOT tutor.first_name + ' ' + tutor.last_name IN $existing_tutors
    WITH tutor, 
         path,
         LENGTH(path) AS path_length,
         tutor.first_name AS first_name,
         tutor.last_name AS last_name,
         [node IN nodes(path) | node.first_name + ' ' + node.last_name] AS path_names
    WITH tutor, first_name, last_name,
         MIN(path_length) AS min_path_length,
         COLLECT(path_names)[0] AS example_path
    RETURN ID(tutor) AS tutor_id,
           first_name,
           last_name,
           min_path_length,
           example_path
    ORDER BY min_path_length, first_name, last_name
    """

    tutors = []
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            query,
            student_first_name=student_first_name,
            student_last_name=student_last_name,
            subject=subject,
            existing_tutors=existing_tutors  # !!! perduodame parametrą
        )

        for record in result:
            data = record.data()
            tutors.append(
                {
                    "tutor_id": str(data.get("tutor_id", "")),
                    "first_name": str(data.get("first_name", "")),
                    "last_name": str(data.get("last_name", "")),
                    "path_length": data.get("min_path_length", 0),
                    "path": data.get("example_path", []),
                }
            )
    return tutors if tutors else None

def search_students(driver, query_text, exclude_element_id=None):
    query = """
    MATCH (s:Student)
    WHERE toLower(s.first_name) CONTAINS toLower($q)
       OR toLower(s.last_name)  CONTAINS toLower($q)
    {exclude_clause}
    RETURN elementId(s) AS id,
           s.first_name AS first_name,
           s.last_name AS last_name,
           s.class_num AS class_num,
           s.school AS school
    LIMIT 25
    """

    exclude_clause = ""
    params = {"q": query_text}

    if exclude_element_id:
        exclude_clause = "AND elementId(s) <> $exclude_id"
        params["exclude_id"] = exclude_element_id

    query = query.format(exclude_clause=exclude_clause)

    results = []
    with driver.session(database=NEO4J_DATABASE) as session:
        data = session.run(query, **params)
        for row in data:
            row = row.data()
            results.append(row)

    return results


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

    friend_req = send_friend_request(driver, "Zigmas", "Zigmaitis", "Petras", "Petraitis")
    print("Zigmo Zigmaičio draugystės prašymas Petrui Petraičiui:", friend_req)

    friend_req = send_friend_request(driver, "Zigmas", "Zigmaitis", "auth", "testas")
    print("Zigmo Zigmaičio draugystės prašymas auth testui:", friend_req)

    sent_requests = get_sent_friend_requests(driver, "Zigmas", "Zigmaitis")
    print(f"Zigmo Zigmaičio išsiųsti draugystės prašymai: {sent_requests}")

    pending = get_pending_friend_requests(driver, "auth", "testas")
    print(f"auth testui išsiųsti draugystės prašymai: {pending}")

    cancel_friend_request(driver, "Zigmas", "Zigmaitis", "auth", "testas")
    print("Zigmo Zigmaičio draugystės prašymas auth testui buvo atšauktas.")

    sent_requests_after_cancel = get_sent_friend_requests(driver, "Zigmas", "Zigmaitis")
    print(f"Zigmo Zigmaičio išsiųsti draugystės prašymai po atšaukimo: {sent_requests_after_cancel}")

    friends = get_friends(driver, "Zigmas", "Zigmaitis")
    print(f"Zigmo Zigmaičio draugai: {friends}")

    decline_friend_request(driver, "Zigmas", "Zigmaitis", "auth", "testas")
    print("auth testas atmetė Zigmo Zigmaičio draugystės prašymą.\n")
    

    subject_tutors = get_subject_tutors_by_student_friends_path_length_to_that_tutor(
        driver, 
        "Zigmas", 
        "Zigmaitis", 
        "Matematika",
        5
    )

    if subject_tutors:
        for tutor in subject_tutors:
            print(f"{tutor['first_name']} {tutor['last_name']}, kelio ilgis: {tutor['path_length']}")
            print(f"  Kelias: {' → '.join(tutor['path'])}")
    else:
        print("Nerasta korepetitorių arba studentas neturi draugų.")
    
    subject_tutors_2 = get_subject_tutors_by_student_friends_path_length_to_that_tutor(
        driver, 
        "Petras", 
        "Petraitis", 
        "Fizika",
        5
    )
    print(f"\nPetro Petraičio draugų korepetitoriai (Fizika, max path 5):")
    if subject_tutors_2:
        for tutor in subject_tutors_2:
            print(f"{tutor['first_name']} {tutor['last_name']}, kelio ilgis:  {tutor['path_length']}")
    else:
        print("Nerasta korepetitorių arba studentas neturi draugų.")
    
    driver.close()