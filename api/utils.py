from datetime import datetime


def parse_date_of_birth(dob: str) -> datetime:
    """ Patikrinti gimimo data. """

    try:
        date_of_birth = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f'gimimo metu formatas netinkamas: {dob} turi buti YYYY-MM-DD')

    if date_of_birth > datetime.now():
        raise ValueError(f"date of birth value is incorrect: {dob}")

    return date_of_birth

def serialize_doc(doc: dict) -> dict:
    """Konvertuoja ObjectId į eilutę JSON grąžinimui."""
    doc["_id"] = str(doc["_id"])
    return doc