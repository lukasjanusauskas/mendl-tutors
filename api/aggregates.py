from bson import ObjectId
from bson.decimal128 import Decimal128
from redis_api.redis_client import get_redis
import os

TUTOR_PAY_PERCENTAGE = 75
REDIS_PASS = os.getenv('REDIS_PASS')
r = get_redis()

def get_tutor_review_count(review_collection, tutor_id: str):
    """
    Apskaičiuoja, kiek atsiliepimų turi konkretus dėstytojas.
    🔹 Naudoja Redis kešą
    🔹 Aktyviai invaliduoja duomenis keičiant
    🔹 Jei atsiliepimų nėra, grąžina 0 ir įrašo į kešą
    """

    cache_key = f"tutor:{tutor_id}:review_count"

    # 1️⃣ Bandome gauti reikšmę iš Redis kešo
    cached_value = r.get(cache_key)
    if cached_value is not None:
        print("⚡️ Grąžiname reikšmę iš Redis kešo")
        return int(cached_value)

    # 2️⃣ Jei keše nėra, atliekame MongoDB agregaciją
    print("📊 Atliekame MongoDB užklausą...")
    aggregate_output_cursor = review_collection.aggregate([
        {
            "$match": {
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [
                    {"type": {"$exists": False}},
                    {"type": {"$ne": "REVOKED"}}
                ]
            }
        },
        {"$count": "num_doc"},
    ])

    # 3️⃣ Nustatome count; jei nėra dokumentų, skaičius = 0
    try:
        agg_doc = next(aggregate_output_cursor)
        count = agg_doc['num_doc']
    except StopIteration:
        count = 0

    # 4️⃣ Įrašome į Redis (net jei count = 0)
    r.set(cache_key, count)

    return count

def invalidate_tutor_review_cache(tutor_id: str):
    """
    Aktyvus kešo išvalymas.
    """
    cache_key = f"tutor:{tutor_id}:review_count"
    deleted = r.delete(cache_key)
    if deleted:
        print(f"🧹 Redis kešas išvalytas dėstytojui {tutor_id}")
    else:
        print(f"ℹ️ Kešas dėstytojui {tutor_id} jau buvo tuščias")

def get_student_review_count(review_collection, student_id: str):
    aggregate_output_cursor = review_collection.aggregate([
        { 
            "$match": {
                "student.student_id": ObjectId(student_id),
                "$or": [ 
                    {"type": {"$exists": False}}, 
                    {"type": {"$ne": "REVOKED"}}
                ]}
        },
        {
            "$count": "num_doc"
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['num_doc']
    except StopIteration:
        return None


def calculate_tutor_rating(review_collection, tutor_id: str):
    aggregate_output_cursor = review_collection.aggregate([
        { 
            "$match": { 
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": { "$ne": "REVOKED" } }
                ], 
                "rating": { "$exists": True } 
            }
        },
        { 
            "$group": { 
                "_id": None,
                "average_rating": { "$avg": "$rating" }
            }
        }
    ])

    try:
        agg_doc = next( aggregate_output_cursor )
        return agg_doc['average_rating']
    except StopIteration:
        return None


def pay_month_tutor(lesson_collection, tutor_id: str):
    """
    Apskaičiuoja mėnesinį atlyginimą dėstytojui pagal pamokas.
    🔹 Naudoja Redis kešą
    🔹 Aktyviai invaliduoja duomenis keičiant
    🔹 Jei pamokų nėra, grąžina 0 ir įrašo į kešą
    """
    cache_key = f"tutor:{tutor_id}:monthly_pay"

    # 1️⃣ Tikriname Redis cache
    cached_value = r.get(cache_key)
    if cached_value is not None:
        print("⚡️ Grąžiname reikšmę iš Redis kešo")
        return float(cached_value)

    # 2️⃣ MongoDB agregacija
    aggregate_output_cursor = lesson_collection.aggregate([
        {
            "$match": {
                "tutor.tutor_id": ObjectId(tutor_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": "ACTIVE" }
                ]
            }
        },
        { "$unwind": "$students" },
        {
            "$group": {
                "_id": None,
                "monthly_pay": {"$sum": "$students.price"}
            }
        }
    ])

    # 3️⃣ Nustatome mėnesinį atlyginimą
    try:
        agg_doc = next(aggregate_output_cursor)
        monthly_pay_raw = agg_doc['monthly_pay']

        # ✅ jei MongoDB grąžina Decimal128, konvertuojame į float
        if isinstance(monthly_pay_raw, Decimal128):
            monthly_pay = float(monthly_pay_raw.to_decimal())
        else:
            monthly_pay = float(monthly_pay_raw)

    except StopIteration:
        monthly_pay = 0

    # 4️⃣ Įrašome į Redis
    r.set(cache_key, monthly_pay)
    return monthly_pay

def invalidate_tutor_pay_cache(tutor_id: str):
    """
    Aktyvus kešo išvalymas mėnesiniam atlyginimui.
    Kvieskite KAI:
    - pridedama nauja pamoka
    - pamoka pašalinama arba keičiasi kaina
    """
    cache_key = f"tutor:{tutor_id}:monthly_pay"
    deleted = r.delete(cache_key)
    if deleted:
        print(f"🧹 Redis kešas mėnesiniam atlyginimui išvalytas dėstytojui {tutor_id}")
    else:
        print(f"ℹ️ Kešas mėnesiniam atlyginimui jau buvo tuščias")



def pay_month_student(lesson_collection, student_id: str):
    """
    Apskaičiuoja mėnesinę sumą, kurią studentas sumokėjo už pamokas.
    🔹 Naudoja Redis kešą
    🔹 Automatiškai konvertuoja Decimal128 į float
    🔹 Jei duomenų nėra, grąžina 0 ir įrašo į kešą
    """
    cache_key = f"student:{student_id}:monthly_pay"

    # 1️⃣ Tikriname Redis cache
    cached_value = r.get(cache_key)
    if cached_value is not None:
        print("⚡️ Grąžiname reikšmę iš Redis kešo")
        return float(cached_value)

    # 2️⃣ MongoDB agregacija
    aggregate_output_cursor = lesson_collection.aggregate([
        {
            "$match": {
                "students.student_id": ObjectId(student_id),
                "$or": [
                    { "type": { "$exists": False } },
                    { "type": "ACTIVE" }
                ]
            }
        },
        { "$unwind": "$students" },
        {
            "$group": {
                "_id": None,
                "monthly_pay": {"$sum": "$students.price"}
            }
        }
    ])

    # 3️⃣ Nustatome mėnesinę sumą
    try:
        agg_doc = next(aggregate_output_cursor)
        monthly_pay_raw = agg_doc['monthly_pay']

        # ✅ jei MongoDB grąžina Decimal128, konvertuojame į float
        if isinstance(monthly_pay_raw, Decimal128):
            monthly_pay = float(monthly_pay_raw.to_decimal())
        else:
            monthly_pay = float(monthly_pay_raw)

    except StopIteration:
        monthly_pay = 0

    # 4️⃣ Įrašome į Redis
    r.set(cache_key, monthly_pay)
    return monthly_pay


# --- Aktyvus Redis kešo invalidavimas ---
def invalidate_student_pay_cache(student_ids):
    """
    Išvalo Redis kešą vienam arba keliems studentams.
    student_ids gali būti:
      - vienas string
      - sąrašas studentų ID
    """
    if isinstance(student_ids, str):
        student_ids = [student_ids]

    for sid in student_ids:
        cache_key = f"student:{sid}:monthly_pay"
        deleted = r.delete(cache_key)
        if deleted:
            print(f"🧹 Redis kešas mėnesinei sumai išvalytas studentui {sid}")
        else:
            print(f"ℹ️ Kešas mėnesinei sumai jau buvo tuščias studentui {sid}")

if __name__ == "__main__":
    from api.connection import get_db
    db = get_db()

    lesson_collection = db['lesson']
    student_collection = db['student']
    tutor_collection = db['tutor']
    review_collection = db['review']

    print(
        pay_month_tutor(lesson_collection, "68e015c72541f9f89f6ca611")
    )