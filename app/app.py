from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)
from pymongo import MongoClient
from dotenv import load_dotenv
import hashlib
import traceback
import jwt
import json

from datetime import datetime, timedelta
from bson import ObjectId
import os
import re

from functools import wraps

from api.tutor import (
    get_tutor_by_id,
    get_tutor_students,
    get_all_tutors,
    delete_tutor,
    create_new_tutor,
    get_tutors_by_name,
    assign_student_to_tutor,
    remove_student_from_tutor
)
from api.student import (
    get_students_tutors,
    create_new_student
)
from api.reviews import (
    create_review,
    list_reviews_student,
    list_reviews_tutor,
    revoke_review,
    get_single_review
)
from api.student import (
    get_all_students,
    get_student_by_id,
    get_students_by_name,
    create_new_student,
    delete_student
)
from api.aggregates import (
    pay_month_student,
    pay_month_tutor,
    calculate_tutor_rating,
    get_student_review_count,
    get_tutor_review_count,
    invalidate_tutor_review_cache,
    invalidate_tutor_pay_cache,
    invalidate_student_pay_cache,
    invalidate_student_review_cache,
    invalidate_tutor_rating_cache
)
from api.lesson import (
    list_lessons_student_week,
    delete_lesson as func_delete_lesson,
    create_lesson,
    change_lesson_date,
    list_lessons_tutor_month,
    list_lesson_student_month
)

from redis_api.redis_client import get_redis
from redis.exceptions import LockError
from cassandra_db.cassandra_client import get_cassandra_session
from flask_socketio import SocketIO, emit, join_room
from cassandra.query import SimpleStatement
from datetime import datetime
from uuid import uuid1
from cassandra.util import uuid_from_time

load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecretkey'
client = MongoClient(os.getenv('MONGO_URI'))
db = client['mendel-tutor']
socketio = SocketIO(app, cors_allowed_origins="*")

r = get_redis()

ADMIN_NAME = os.getenv('ADMIN_NAME')
ADMIN_PASS = os.getenv('ADMIN_PASS')

ADMIN_TYPE = 'admin'
TUTOR_TYPE = 'tutor'
STUDENT_TYPE = 'student'

JWT_SECRET_KEY = 'labai-slaptas-raktas-1'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 1

session_cassandra = get_cassandra_session()


@app.route("/")
def index():
    if 'session_type' in session:
        session_type = session['session_type']
    else:
        session_type = None

    return render_template("index.html", session_type=session_type)


@app.before_request
def check_session_type():
    if request.endpoint in ('login', 'logout', 'test_jwt'):
        return None

    if request.endpoint and request.endpoint.startswith('sign_up'):
        return None

    # Check JWT token instead of session
    if 'jwt_token' not in session:
        return redirect(url_for('login'))

    payload = verify_jwt_token(session['jwt_token'])
    if not payload:
        session.clear()  # Clear invalid session
        return redirect(url_for('login'))

    # Store user info in request context for easy access
    request.current_user = payload

    admin_only = [
        'add_student_to_tutor',
        'delete_student_ui',
        'remove_tutor',
        'students',
        'tutors',
        'add_student',
        'add_tutor'
    ]

    if payload.get('user_type') == ADMIN_TYPE:
        return

    elif request.endpoint in admin_only:
        flash("Neesate autorizuoti", "warning")
        return redirect(url_for("index"))


def check_student_session(session, student_id: str):
    # Check JWT token
    if 'jwt_token' not in session:
        return False

    payload = verify_jwt_token(session['jwt_token'])
    if not payload:
        return False

    # Admin can access everything
    if payload.get('user_type') == ADMIN_TYPE:
        return True

    # Student can only access their own data
    if payload.get('user_type') == STUDENT_TYPE and payload.get('user_id') == str(student_id):
        return True

    return False


def check_tutor_session(session, tutor_id: str):
    # Check JWT token
    if 'jwt_token' not in session:
        return False

    payload = verify_jwt_token(session['jwt_token'])
    if not payload:
        return False

    # Admin can access everything
    if payload.get('user_type') == ADMIN_TYPE:
        return True

    # Tutor can only access their own data
    if payload.get('user_type') == TUTOR_TYPE and payload.get('user_id') == str(tutor_id):
        return True

    return False


@app.route('/students')
def students():
    """
    Puslapis su visų studentų sąrašu ir paieškos galimybe pagal vardą ir pavardę.
    """
    try:
        first_name = request.args.get("first_name")
        last_name = request.args.get("last_name")
        student_collection = db["student"]

        if first_name and last_name:
            students_list = get_students_by_name(student_collection, first_name, last_name)
        else:

            students_list = list(
                student_collection.find({}).sort([("first_name", 1), ("last_name", 1)])
            )

        if first_name is None:
            return render_template(
                "students.html",
                students=students_list,
                first_name="Vardas",
                last_name="Pavardė"
            )
        else:
            return render_template(
                "students.html",
                students=students_list,
                first_name=first_name,
                last_name=last_name
            )

    except Exception as e:
        return f"Klaida: {e}", 500


@app.route("/student/<student_id>")
def view_student(student_id):
    if not check_student_session(session, student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        student = get_student_by_id(db["student"], student_id)
        tutors = []

        tutors_cursor = db.tutor.find({"students_subjects.student.student_id": student_id})

        review_count = get_student_review_count(db['review'],
                                                student_id=student['_id'])
        if review_count:
            student['review_count'] = review_count

        pay = pay_month_student(db['lesson'], student_id=student['_id'])
        if pay:
            student['pay'] = pay

        lessons = []
        try:
            lessons = list_lessons_student_week(
                db["lesson"],
                db["student"],
                str(student['_id'])
            )
        except Exception as lesson_e:
            print(f"Error fetching lessons: {lesson_e}")

        for t in tutors_cursor:
            tutors.append({
                "_id": str(t.get("_id")),
                "first_name": t.get("first_name", ""),
                "last_name": t.get("last_name", ""),
                "email": t.get("email", ""),
                "subject": ", ".join(
                    [s.get("subject", "") for s in t.get("subjects", [])]
                )
            })

        return render_template("student.html", student=student, tutors=tutors, lessons=lessons)
    except Exception as e:
        traceback.print_exc()
        return render_template("student.html", student=None, tutors=None, lessons=[], error=str(e))


@app.route("/student/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        try:
            data = {
                "first_name": request.form["first_name"],
                "last_name": request.form["last_name"],
                "second_name": request.form.get("second_name"),
                "class": int(request.form["class"]),
                "date_of_birth": request.form["date_of_birth"],
                "subjects": [s.strip() for s in request.form["subjects"].split(",")],
                "parents_phone_numbers": [p.strip() for p in request.form["parents_phone_numbers"].split(",")],
                "student_phone_number": request.form.get("student_phone_number"),
                "student_email": request.form.get("student_email"),
                "parents_email": request.form.get("parents_email"),
                "password": request.form["password"]
            }

            data = {k: v for k, v in data.items() if v not in [None, ""]}

            try:
                create_new_student(db.student, data)
                flash("Mokinys sėkmingai pridėtas!", "success")
                return redirect(url_for("students"))

            except LockError:
                flash("Mokinių sąrašas šiuo metu redaguojamas kito naudotojo, pabandykite vėliau.", "warning")
                return redirect(url_for("students"))

        except Exception as e:
            flash(str(e), "danger")

    return render_template("add_student.html")


@app.route("/student/<student_id>/delete", methods=["GET", "POST"])
def delete_student_ui(student_id):
    try:
        try:
            result = delete_student(db.student, db.tutor, student_id)

            if result["deleted"]:
                flash("Mokinys sėkmingai ištrintas!", "success")
            else:
                flash("Mokinys nerastas.", "warning")

        except LockError:
            flash("Šiuo metu mokinys redaguojamas kito naudotojo, pabandykite vėliau.", "warning")

    except Exception as e:
        flash(str(e), "danger")

    return redirect(url_for("students"))


@app.route('/sign-up', methods=['GET'])
def sign_up_all():
    return render_template("sign_up_all.html")


@app.route('/sign-up-student', methods=['GET', 'POST'])
def sign_up_student():
    if request.method == 'POST':
        try:
            # Validate and prepare data before sending to API
            # Convert class to integer
            try:
                class_value = int(request.form['class'])
                if class_value < 1 or class_value > 12:
                    raise ValueError("Klasė turi būti nuo 1 iki 12")
            except (ValueError, TypeError):
                raise ValueError("Klasė turi būti skaičius nuo 1 iki 12")

            # Validate parents phone numbers
            parents_phones_raw = request.form.get('parents_phone_numbers', '')
            if not parents_phones_raw.strip():
                raise ValueError("Būtina nurodyti bent vieną tėvų telefono numerį")

            parents_phones_list = [p.strip() for p in parents_phones_raw.split(',') if p.strip()]
            if not parents_phones_list:
                raise ValueError("Būtina nurodyti bent vieną tėvų telefono numerį")

            # Validate phone number format
            phone_pattern = r'^\+?\d{7,15}$'
            for i, phone in enumerate(parents_phones_list):
                if not re.match(phone_pattern, phone):
                    raise ValueError(
                        f"Neteisingas telefono numerio formatas: '{phone}'. Telefono numeris turi būti 7-15 skaitmenų, gali prasidėti '+' ženklu")

            # Validate student phone number if provided
            student_phone = request.form.get('phone_number', '').strip()
            if student_phone and not re.match(phone_pattern, student_phone):
                raise ValueError(
                    f"Neteisingas mokinio telefono numerio formatas: '{student_phone}'. Telefono numeris turi būti 7-15 skaitmenų, gali prasidėti '+' ženklu")

            # Paruošiame duomenis API funkcijai
            student_info = {
                'first_name': request.form['first_name'],
                'last_name': request.form['last_name'],
                'date_of_birth': request.form['date_of_birth'],
                'class': class_value,
                'password': request.form['password'],
                'parents_phone_numbers': parents_phones_list
            }

            # Neprivalomi laukai
            if request.form.get('second_name'):
                student_info['second_name'] = request.form['second_name']
            if student_phone:
                student_info['phone_number'] = student_phone
            if request.form.get('student_email'):
                student_info['student_email'] = request.form['student_email']
            if request.form.get('parents_email'):
                student_info['parents_email'] = request.form['parents_email']

            # Subjects - konvertuojame iš string į list
            subjects_raw = request.form.get('subjects', '')
            if subjects_raw:
                subjects_list = [s.strip() for s in subjects_raw.split(',') if s.strip()]
                student_info['subjects'] = subjects_list
            else:
                student_info['subjects'] = []

            # Sukuriame studentą
            new_student = create_new_student(db.student, student_info)
            student_id = new_student.inserted_id

            session['user_id'] = str(student_id)
            session['session_type'] = STUDENT_TYPE
            session['user_name'] = f"{student_info['first_name']} {student_info['last_name']}"
            session['logged_in'] = True

            flash('Studentas sėkmingai užregistruotas!', 'success')
            return redirect(url_for('view_student', student_id=new_student.inserted_id))

        except Exception as e:
            return render_template('sign_up_student.html', error=str(e))

    # GET request
    return render_template('sign_up_student.html')


@app.route('/sign-up-tutor', methods=['GET', 'POST'])
def sign_up_tutor():
    if request.method == 'POST':
        try:
            tutor_info = {
                "first_name": request.form['first_name'],
                "last_name": request.form['last_name'],
                "date_of_birth": request.form['date_of_birth'],
                "email": request.form['email'],
                "password": request.form['password'],
                "subjects": []
            }

            # Neprivalomi laukai
            second_name = request.form.get('second_name')
            if second_name:
                tutor_info['second_name'] = second_name

            phone = request.form.get('phone_number')
            if phone:
                tutor_info['phone_number'] = phone

            # Apdorojame dalykus ir klases
            subjects_raw = request.form.getlist('subjects')
            if not subjects_raw:
                raise ValueError("Būtina pasirinkti bent vieną dėstomą dalyką")

            for subject in subjects_raw:
                max_class_key = f"max_class_{subject}"
                max_class = request.form.get(max_class_key, 12)
                tutor_info['subjects'].append({
                    "subject": subject,
                    "max_class": int(max_class)
                })

            insert_res = create_new_tutor(db.tutor, tutor_info)
            tutor_id = insert_res.inserted_id

            session['user_id'] = str(tutor_id)
            session['session_type'] = STUDENT_TYPE
            session['user_name'] = f"{tutor_info['first_name']} {tutor_info['last_name']}"
            session['logged_in'] = True

            flash("Korepetitorius sėkmingai užregistruotas!", "success")
            return redirect(url_for("view_tutor", tutor_id=tutor_id))

        except Exception as e:
            return render_template('sign_up_tutor.html', error=str(e))

    # GET užklausa
    return render_template('sign_up_tutor.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            # Check if user is a tutor
            tutor = db.tutor.find_one({"email": email})
            if tutor:
                password_encoded = password.encode('utf-8')
                hash_algo = hashlib.sha256()
                hash_algo.update(password_encoded)
                hashed_password = hash_algo.hexdigest()

                if tutor.get('password_hashed') == hashed_password:
                    token = generate_jwt_token(str(tutor['_id']), TUTOR_TYPE,
                                               f"{tutor['first_name']} {tutor['last_name']}")

                    redis_key = f"jwt:user:{tutor['_id']}"

                    # Store tokens in JSON format
                    token_data = {
                        'token': token,
                        'user_type': TUTOR_TYPE,
                        'user_id': str(tutor['_id']),
                        'user_name': f"{tutor['first_name']} {tutor['last_name']}"
                    }

                    # Store in Redis
                    r.setex(redis_key, JWT_EXPIRATION_HOURS * 3600, json.dumps(token_data))

                    session['jwt_token'] = token
                    session['user_id'] = str(tutor['_id'])
                    session['session_type'] = TUTOR_TYPE
                    session['user_name'] = f"{tutor['first_name']} {tutor['last_name']}"
                    session['logged_in'] = True

                    flash('Sėkmingai prisijungėte!', 'success')
                    return redirect(url_for('view_tutor', tutor_id=str(tutor['_id'])))

            student = db.student.find_one({"student_email": email})
            if student:
                password_encoded = password.encode('utf-8')
                hash_algo = hashlib.sha256()
                hash_algo.update(password_encoded)
                hashed_password = hash_algo.hexdigest()

                if student.get('password_hashed') == hashed_password:
                    token = generate_jwt_token(str(student['_id']), STUDENT_TYPE,
                                               f"{student['first_name']} {student['last_name']}")

                    redis_key = f"jwt:user:{student['_id']}"
                    token_data = {'token': token, 'user_type': STUDENT_TYPE, 'user_id': str(student['_id']),
                                  'user_name': f"{student['first_name']} {student['last_name']}"}
                    r.setex(redis_key, JWT_EXPIRATION_HOURS * 3600, json.dumps(token_data))

                    session['jwt_token'] = token
                    session['user_id'] = str(student['_id'])
                    session['session_type'] = STUDENT_TYPE
                    session['user_name'] = f"{student['first_name']} {student['last_name']}"

                    flash('Sėkmingai prisijungėte!', 'success')
                    return redirect(url_for('view_student', student_id=str(student['_id'])))

            # Admin
            if email == ADMIN_NAME and password == ADMIN_PASS:
                token = generate_jwt_token('admin', ADMIN_TYPE, 'Administrator')

                redis_key = "jwt:user:admin"
                token_data = {'token': token, 'user_type': ADMIN_TYPE, 'user_id': 'admin', 'user_name': 'Administrator'}
                r.setex(redis_key, JWT_EXPIRATION_HOURS * 3600, json.dumps(token_data))

                session['jwt_token'] = token
                session['session_type'] = ADMIN_TYPE
                session['logged_in'] = True

                flash('Sėkmingai prisijungėte!', 'success')
                return redirect(url_for('index'))

            return render_template('login.html', error='Neteisingas el. paštas arba slaptažodis')

        except Exception as e:
            return render_template('login.html', error=str(e))

    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        redis_key = f"jwt:user:{session['user_id']}"
        r.delete(redis_key)

    session.clear()
    flash('Sėkmingai atsijungėte!', 'info')
    return redirect(url_for('login'))


@app.route("/tutors", methods=["GET"])
def tutors():
    """
    Puslapis su visų korepetitorių sąrašu ir paieškos galimybe pagal vardą ir pavardę.
    """
    try:
        first_name = request.args.get("first_name", "").strip()
        last_name = request.args.get("last_name", "").strip()
        tutor_collection = db["tutor"]

        if first_name or last_name:
            tutors_list = get_tutors_by_name(tutor_collection, first_name, last_name)
        else:
            tutors_list = list(
                tutor_collection.find({}).sort([("first_name", 1), ("last_name", 1)])
            )

        return render_template(
            "tutors.html",
            tutors=tutors_list,
            first_name=first_name,
            last_name=last_name
        )
    except Exception as e:
        return f"Klaida: {e}", 500


@app.route("/tutor/<tutor_id>/view")
def view_tutor(tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        tutor = get_tutor_by_id(db.tutor, tutor_id)

        rating = calculate_tutor_rating(db['review'], tutor['_id'])
        if rating:
            tutor['rating'] = rating

        review_count = get_tutor_review_count(db['review'], tutor_id=tutor['_id'])
        if review_count:
            tutor['review_count'] = review_count

        pay = pay_month_tutor(db['lesson'], tutor_id=tutor['_id'])
        if pay:
            tutor['pay'] = pay

        if not tutor:
            return render_template("tutor.html", tutor=None, students=None)

        students = get_tutor_students(db.tutor, tutor_id)
        return render_template("tutor.html", tutor=tutor, students=students)

    except Exception as e:
        return render_template("tutor.html", tutor=None, students=None, error=str(e))


@app.route("/tutors/<tutor_id>/delete", methods=["GET", "POST"])
def remove_tutor(tutor_id):
    try:
        try:
            result = delete_tutor(db.tutor, tutor_id)

            if result["deleted"]:
                flash("Korepetitorius sėkmingai ištrintas!", "success")
            else:
                flash("Korepetitorius nerastas.", "warning")

        except LockError:
            flash("Šiuo metu korepetitorius redaguojamas kito naudotojo, pabandykite vėliau.", "warning")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("tutors"))


@app.route("/tutors/add", methods=["GET", "POST"])
def add_tutor():
    if request.method == "POST":
        try:
            tutor_info = {
                "first_name": request.form['first_name'],
                "last_name": request.form['last_name'],
                "date_of_birth": request.form['date_of_birth'],
                "email": request.form['email'],
                "password": request.form['password'],
                "subjects": []
            }

            # Nebūtini laukai
            second_name = request.form.get('second_name')
            if second_name:
                tutor_info['second_name'] = second_name

            phone = request.form.get('phone_number')
            if phone:
                tutor_info['phone_number'] = phone

            # Gauti pasirinktus dalykus ir jų klases
            subjects_raw = request.form.getlist('subjects')
            for subject in subjects_raw:
                max_class_key = f"max_class_{subject}"
                max_class = request.form.get(max_class_key, 12)
                tutor_info['subjects'].append({
                    "subject": subject,
                    "max_class": int(max_class)
                })

            create_new_tutor(db.tutor, tutor_info)
            flash("Korepetitorius sėkmingai pridėtas!", "success")
            return redirect(url_for("tutors"))
        except Exception as e:
            flash(str(e), "danger")

    return render_template("add_tutor.html")


@app.route('/tutor/<tutor_id>/create_review', methods=['GET', 'POST'])
def add_new_review_tutor(tutor_id):
    """
    Leidžia dėstytojui sukurti atsiliepimą savo mokiniui.
    Pridedant naują atsiliepimą:
    įrašome jį į MongoDB
    aktyviai išvalome Redis kešą (kad kito kvietimo metu duomenys būtų atnaujinti)
    """

    # Gauname korepetitoriaus informaciją
    tutor = get_tutor_by_id(db['tutor'], tutor_id)
    if not tutor:
        flash('Korepetitorius nerastas', 'danger')
        return redirect(url_for('index'))

    # Gauti mokinius iš duomenų bazės
    students = get_tutor_students(db['tutor'], tutor_id)

    # Paruošiame dictionary {student_id: "Vardas Pavardė"}
    students = {stud['student_id']: f"{stud['first_name']} {stud['last_name']}"
                for stud in students}

    # Jei dėstytojas neturi mokinių
    if not students:
        flash('Jūs neturite mokinių', 'warning')
        return redirect("/")

    # Apdorojame POST užklausą (forma pateikta)
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        review_text = request.form.get('review_text')

        # Išsaugome atsiliepimą MongoDB duomenų bazėje
        create_review(
            db['review'], db['tutor'], db['student'],
            review_info={
                'tutor_id': tutor_id,
                'student_id': student_id,
                'for_tutor': False,
                'review_text': review_text
            }
        )

        invalidate_student_review_cache(student_id)

        flash('Atsiliepimas sėkmingai pateiktas!', 'success')
        return redirect(url_for('view_tutor', tutor_id=tutor_id))

    # GET užklausa – rodome formą
    return render_template('review_tutor.html', students=students, tutor_id=tutor_id, tutor=tutor)


@app.route('/student/<student_id>/create_review', methods=['GET', 'POST'])
def add_new_review_student(student_id):
    """
    Leidžia studentui sukurti atsiliepimą savo dėstytojui.
    Įrašius atsiliepimą:
        - įrašome į MongoDB
        - aktyviai išvalome Redis kešą dėstytojui
    """

    # Gauname mokinio informaciją
    student = get_student_by_id(db['student'], student_id)
    if not student:
        flash('Studentas nerastas', 'danger')
        return redirect(url_for('index'))

    # Patikriname studento sesiją
    if not check_student_session(session, student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    # Gauti studento priskirtus dėstytojus
    try:
        tutors = get_students_tutors(db['tutor'], student_id)
    except AssertionError:
        flash('Jūs neturite priskirtų mokytojų', 'warning')
        return redirect("/")

    # Sukuriame dictionary {tutor_id: "Vardas Pavardė"}
    tutors = {str(tut['_id']): f"{tut['first_name']} {tut['last_name']}" for tut in tutors}

    # Jei nėra priskirtų dėstytojų
    if not tutors:
        flash('Jūs neturite priskirtų mokytojų', 'warning')
        return redirect("/")

    # POST užklausa (forma pateikta)
    if request.method == 'POST':
        tutor_id = request.form.get('tutor_id')
        review_text = request.form.get('review_text')
        rating = request.form.get('rating')

        # Išsaugome atsiliepimą MongoDB
        create_review(
            db['review'], db['tutor'], db['student'],
            review_info={
                'tutor_id': tutor_id,
                'student_id': student_id,
                'for_tutor': True,
                'review_text': review_text,
                'rating': int(rating)
            }
        )

        # Aktyviai išvalome Redis kešą – dėstytojo peržiūrų skaičius gali pasikeisti
        invalidate_tutor_review_cache(tutor_id)
        invalidate_tutor_rating_cache(tutor_id)

        flash('Atsiliepimas sėkmingai pateiktas!', 'success')
        return redirect("/")

    # GET užklausa – rodome formą
    return render_template('review_student.html', tutors=tutors, student_id=student_id, student=student)


@app.route('/student/<student_id>/payment', methods=['GET', 'POST'])
def payment_student(student_id):
    """
    Leidžia studentui sukurti apmokėjimą savo dėstytojui.
    """

    # Gauname mokinio informaciją
    student = get_student_by_id(db['student'], student_id)
    if not student:
        flash('Studentas nerastas', 'danger')
        return redirect(url_for('index'))

    # Patikriname studento sesiją
    if not check_student_session(session, student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    # Gauti studento priskirtus dėstytojus
    try:
        tutors = get_students_tutors(db['tutor'], student_id)
    except AssertionError:
        flash('Jūs neturite priskirtų mokytojų', 'warning')
        return redirect("/")

    # Sukuriame dictionary {tutor_id: "Vardas Pavardė"}
    tutors = {str(tut['_id']): f"{tut['first_name']} {tut['last_name']}" for tut in tutors}

    # Jei nėra priskirtų dėstytojų
    if not tutors:
        flash('Jūs neturite priskirtų mokytojų', 'warning')
        return redirect("/")

    # POST užklausa (forma pateikta)
    if request.method == 'POST':
        tutor_id = request.form.get('tutor_id')
        payment_amount = request.form.get('payment_amount')

        # Išsaugome atsiliepimą Cassandra duomenų bazėje
        # create_payment()

        flash('Mokėjimas sėkmingai atliktas!', 'success')
        return redirect("/")

    # GET užklausa – rodome formą
    return render_template('payment_student.html', tutors=tutors, student_id=student_id, student=student)


@app.route('/tutor/<tutor_id>/review_list', methods=['GET'])
def show_reviews_tutor(tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    recieved_reviews, written_reviews = list_reviews_tutor(db['review'], tutor_id)

    tutor = get_tutor_by_id(db['tutor'], tutor_id)
    if not tutor:
        flash('Korepetitorius nerastas', 'danger')
        return redirect(url_for('index'))

    return render_template('review_view.html',
                           tutor_id=tutor_id,
                           written_reviews=written_reviews,
                           recieved_reviews=recieved_reviews,
                           tutor=tutor)


@app.route("/tutor/<tutor_id>/add_student", methods=["GET", "POST"])
def add_student_to_tutor(tutor_id):
    try:
        tutor = get_tutor_by_id(db.tutor, tutor_id)
        if not tutor:
            flash("Korepetitorius nerastas.", "danger")
            return redirect(url_for("tutors"))

        if request.method == "POST":
            student_id = request.form.get("student_id")
            subject = request.form.get("subject")

            try:
                try:
                    result = assign_student_to_tutor(
                        db.tutor,
                        db.student,
                        tutor_id,
                        student_id,
                        subject
                    )
                    if result.modified_count > 0:
                        flash("Mokinys sėkmingai priskirtas!", "success")
                        return redirect(url_for("view_tutor", tutor_id=tutor_id))
                    else:
                        flash("Nepavyko priskirti mokinio.", "danger")

                except LockError:
                    flash('Korepetitorius šiuo metu redaguojamas kito naudotojo, pabandykite vėliau.', 'warning')
                    return redirect(url_for('view_tutor', tutor_id=tutor_id))

            except Exception as e:
                flash(f"Klaida: {str(e)}", "danger")

        students = get_all_students(db.student)
        return render_template("add_student_to_tutor.html",
                               tutor=tutor,
                               students=students)

    except Exception as e:
        flash(f"Klaida: {str(e)}", "danger")
        return redirect(url_for("view_tutor", tutor_id=tutor_id))


@app.route("/tutor/<tutor_id>/remove_student/<student_id>", methods=["POST"])
def remove_student_from_tutor_route(tutor_id, student_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        try:
            result = remove_student_from_tutor(db.tutor, tutor_id, student_id)

            if result["removed"]:
                flash("Mokinys sėkmingai pašalintas!", "success")
            else:
                flash("Nepavyko pašalinti mokinio.", "danger")

        except LockError:
            flash('Korepetitorius šiuo metu redaguojamas kito naudotojo, pabandykite vėliau.', 'warning')

    except Exception as e:
        flash(f"Nepavyko pašalinti mokinio: {str(e)}", "danger")

    return redirect(url_for("view_tutor", tutor_id=tutor_id))


@app.route('/student/<student_id>/review_list', methods=['GET'])
def show_reviews_student(student_id):
    if not check_student_session(session, student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    recieved_reviews, written_reviews = list_reviews_student(db['review'], student_id)

    student = get_student_by_id(db['student'], student_id)
    if not student:
        flash('Studentas nerastas', 'danger')
        return redirect(url_for('index'))

    return render_template('review_view_student.html',
                           student_id=student_id,
                           written_reviews=written_reviews,
                           recieved_reviews=recieved_reviews,
                           student=student)


@app.route('/tutor/revoke_review/<tutor_id>/<review_id>', methods=['GET'])
def tutor_revoke_review(tutor_id, review_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    tutor = get_tutor_by_id(db['tutor'], tutor_id)
    if not tutor:
        flash('Korepetitorius nerastas', 'danger')
        return redirect(url_for('index'))

    try:
        review = db['review'].find_one({"_id": ObjectId(review_id)})
        student_oid = review.get("student", {}).get("student_id")
        student_id_str = str(student_oid)
        invalidate_student_review_cache(student_id_str)
        revoke_review(db['review'], review_id)

    except Exception as err:
        flash(str(err), 'danger')

    flash('Sėkmingai atsiimtas atsiliepimas', 'success')

    return redirect(url_for('show_reviews_tutor', tutor_id=tutor_id, tutor=tutor))


@app.route('/student/revoke_review/<student_id>/<review_id>', methods=['GET'])
def student_revoke_review(student_id, review_id):
    if not check_student_session(session, student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        review = db['review'].find_one({"_id": ObjectId(review_id)})
        tutor_oid = review.get("tutor", {}).get("tutor_id")
        tutor_id_str = str(tutor_oid)
        invalidate_tutor_review_cache(tutor_id_str)
        invalidate_tutor_rating_cache(tutor_id_str)
        revoke_review(db['review'], review_id)
    except Exception as err:
        flash(str(err), 'danger')

    flash('Sėkmingai atsiimtas atsiliepimas', 'success')

    return redirect(url_for('show_reviews_student', student_id=student_id))


@app.route('/review/revoke/tutor/<review_id>/<tutor_id>', methods=['GET'])
def revoke_review_dialog_tutor(review_id, tutor_id):
    """ View and (optionally) revoke review"""
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        review = get_single_review(db['review'], review_id=review_id)

    except ValueError:
        flash('Could not find review', 'danger')
        redirect(url_for('show_reviews_tutor', tutor_id=tutor_id))

    return render_template('revoke_review.html',
                           review=review,
                           review_id=review_id,
                           tutor_id=tutor_id)


@app.route('/review/revoke/student/<review_id>/<student_id>', methods=['GET'])
def revoke_review_dialog_student(review_id, student_id):
    """ View and (optionally) revoke review"""
    if not check_student_session(session, student_id=student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    if not check_student_session(session, student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        review = get_single_review(db['review'], review_id=review_id)

    except ValueError:
        flash('Could not find review', 'danger')
        redirect(url_for('show_reviews_student', tutor_id=student_id))

    return render_template('revoke_review_student.html',
                           review=review,
                           review_id=review_id,
                           student_id=student_id)


@app.route("/tutor/manage_lessons/<tutor_id>", methods=['GET'])
def manage_lessons(tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    tutor = get_tutor_by_id(db['tutor'], tutor_id)
    if not tutor:
        flash('Korepetitorius nerastas', 'danger')
        return redirect(url_for('index'))

    list_lessons = list_lessons_tutor_month(
        db['lesson'],
        db['tutor'],
        tutor_id,
        year=str(datetime.now().year),
        month=str(datetime.now().month)
    )

    return render_template(
        'lesson_main.html',
        tutor_id=tutor_id,
        lessons=list_lessons,
        tutor=tutor
    )


@app.route("/tutor/change_lesson_time/<lesson_id>/<tutor_id>", methods=["POST"])
def change_lesson_time(lesson_id, tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    date = request.form.get("date")
    time = request.form.get("time")

    try:
        new_time = f"{date} {time:0>{2}}:00"
        change_lesson_date(db['lesson'], lesson_id, new_time)

        flash(f"Sėkmingai perkelta pamoka", "success")

    except LockError:
        flash(f'Nepavyko perkelti pamokos, ją šiuo metu redaguoja kitas naudotojas', 'warning')

    except Exception as e:
        flash(f'Nepavyko perkelti pamokos {e}', 'warning')

    return redirect(url_for('manage_lessons', tutor_id=tutor_id))


@app.route("/tutor/create_lesson/<tutor_id>", methods=["GET", "POST"])
def create_new_lesson(tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    tutor = get_tutor_by_id(db['tutor'], tutor_id)
    if not tutor:
        flash('Korepetitorius nerastas', 'danger')
        return redirect(url_for('index'))

    if request.method == "POST":
        # Get request data
        date_of_lesson = request.form.get('date')
        hour = request.form.get('hour')
        student_ids = request.form.getlist('student_ids[]')
        subject = request.form.get('subject')

        # Post the lesson
        try:
            create_lesson(
                db['lesson'],
                db['tutor'],
                db['student'],
                lesson_info={
                    'time': f'{date_of_lesson} {hour:0>{2}}:00',
                    'tutor_id': tutor_id,
                    'student_ids': student_ids,
                    'subject': subject,
                }
            )

        except Exception as e:
            traceback.print_exc()
            flash(f"Nepavyko sukurti pamokos: {e}", "alert")
            return redirect(url_for('create_new_lesson', tutor_id=tutor_id, tutor=tutor))

        flash(f"Pavyko sukurti pamoką", "success")
        invalidate_tutor_pay_cache(tutor_id)
        invalidate_student_pay_cache(student_ids)
        return redirect(url_for('manage_lessons', tutor_id=tutor_id, tutor=tutor))

    else:
        # Get list of students
        students = get_tutor_students(db['tutor'], tutor_id=tutor_id)

        # Show template
        return render_template('create_lesson.html', tutor_id=tutor_id, students=students, tutor=tutor)


@app.route("/tutor/delete_lesson/<lesson_id>/<tutor_id>", methods=["GET", "POST"])
def delete_lesson(lesson_id, tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    try:
        # Paimame studentų ID prieš trinant pamoką
        lesson = db['lesson'].find_one({"_id": ObjectId(lesson_id)})
        if lesson is None:
            flash("Pamoka nerasta", "warning")
            return redirect(url_for("manage_lessons", tutor_id=tutor_id))

        student_ids = [str(s["student_id"]) for s in lesson.get("students", [])]

        # Triname pamoką
        func_delete_lesson(db['lesson'], lesson_id)
        flash("Pavyko panaikinti pamoką", "success")

        # Išvalome Redis kešus
        invalidate_tutor_pay_cache(tutor_id)
        invalidate_student_pay_cache(student_ids)

    except LockError:
        flash(f"Šiuo metu pamoką redaguoja kitas naudotojas, pabandykite vėliau.", "alert")

    except Exception as e:
        flash(f"Nepavyko ištrinti pamokos: {e}", "warning")

    return redirect(url_for("manage_lessons", tutor_id=tutor_id))


@app.route("/tutor/edit_lesson/<lesson_id>/<tutor_id>", methods=["GET", "POST"])
def edit_lesson(lesson_id, tutor_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    tutor = get_tutor_by_id(db['tutor'], tutor_id)
    if not tutor:
        flash("Korepetitorius nerastas", "warning")
        return redirect(url_for("index"))

    lesson = db['lesson'].find_one({'_id': ObjectId(lesson_id)})
    return render_template("edit_lesson.html", lesson=lesson, tutor_id=tutor_id, tutor=tutor)


def generate_jwt_token(user_id, user_type, user_name):
    """Generate a JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'user_type': user_type,
        'user_name': user_name,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()  # issued at
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_jwt_token(token):
    """Verify and decode a JWT token, checking Redis storage"""
    try:
        # First, decode the JWT to get the payload
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Get user_id from payload
        user_id = payload.get('user_id')

        # Check if token exists in Redis
        redis_key = f"jwt:user:{user_id}"
        stored_data = r.get(redis_key)

        if not stored_data:
            # Token not found in Redis (expired or logged out)
            return None

        # Parse stored data
        token_data = json.loads(stored_data)

        # Verify that the token matches what's stored
        if token_data.get('token') != token:
            # Token mismatch - possible security issue
            return None

        return payload

    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Token is invalid
    except Exception as e:
        print(f"Error verifying token: {e}")
        return None


def jwt_required(f):
    """Decorator to require JWT authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Check for token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                token = auth_header.split(" ")[1]  # Format: "Bearer <token>"
            except IndexError:
                return {'error': 'Invalid authorization header format'}, 401

        # Check for token in session (for web interface)
        if not token and 'jwt_token' in session:
            token = session['jwt_token']

        if not token:
            flash('Token is missing', 'warning')
            return redirect(url_for('login'))

        payload = verify_jwt_token(token)
        if payload is None:
            flash('Token is invalid or expired', 'warning')
            session.pop('jwt_token', None)  # Remove invalid token
            return redirect(url_for('login'))

        # Add user info to request context
        request.current_user = payload
        return f(*args, **kwargs)

    return decorated_function


@app.route('/test-jwt')
def test_jwt():
    """Test route to check JWT functionality"""
    if 'jwt_token' not in session:
        return {
            'error': 'No JWT token in session',
            'session_keys': list(session.keys()),
            'logged_in': session.get('logged_in', False)
        }

    token = session['jwt_token']
    payload = verify_jwt_token(token)

    if payload:
        return {
            'status': 'JWT working correctly',
            'token_preview': token[:50] + '...',
            'payload': payload,
            'expires_at': datetime.fromtimestamp(payload['exp']).isoformat(),
            'issued_at': datetime.fromtimestamp(payload['iat']).isoformat(),
            'time_until_expiry': payload['exp'] - datetime.utcnow().timestamp()
        }
    else:
        return {
            'error': 'JWT token is invalid or expired',
            'token_preview': token[:50] + '...'
        }


def get_chat_context(user_role, user_id, other_id):
    """
    Универсальная функция для подготовки контекста чата.
    user_role: "tutor" или "student" — роль текущего пользователя
    user_id: ID текущего пользователя
    other_id: ID второго участника
    """
    if user_role == "tutor":
        tutor = get_tutor_by_id(db.tutor, user_id)
        student = get_student_by_id(db.student, other_id)
    else:
        student = get_student_by_id(db.student, user_id)
        tutor = get_tutor_by_id(db.tutor, other_id)

    if not tutor or not student:
        return None, None, None

    return tutor, student, user_role


@app.route("/tutor/<tutor_id>/chat/<student_id>")
def chat_with_student(tutor_id, student_id):
    if not check_tutor_session(session, tutor_id=tutor_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    tutor, student, role = get_chat_context("tutor", tutor_id, student_id)
    if not tutor or not student:
        flash("Korepetitorius arba mokinys nerastas.", "danger")
        return redirect(url_for("view_tutor", tutor_id=tutor_id))

    return render_template("chat.html", tutor=tutor, student=student, sender_role=role)


@app.route("/student/<student_id>/chat/<tutor_id>")
def chat_with_tutor(student_id, tutor_id):
    if not check_student_session(session, student_id=student_id):
        flash("Nesate autorizuotas šiam puslapiui", "warning")
        return redirect(url_for("index"))

    tutor, student, role = get_chat_context("student", student_id, tutor_id)
    if not tutor or not student:
        flash("Studentas arba korepetitorius nerastas.", "danger")
        return redirect(url_for("view_student", student_id=student_id))

    return render_template("chat.html", tutor=tutor, student=student, sender_role=role)


@socketio.on("join")
def handle_join(data):
    tutor_id = data["tutor_id"]
    student_id = data["student_id"]
    room = f"{tutor_id}_{student_id}"
    join_room(room)

    query = f"""
        SELECT sender_role, message_text, sent_at 
        FROM messages.by_pair 
        WHERE tutor_id = %s AND student_id = %s 
        LIMIT 50
    """
    rows = session_cassandra.execute(query, (tutor_id, student_id))
    messages = [
        {
            "sender": row.sender_role,
            "message": row.message_text,
            "timestamp": row.sent_at.isoformat() if row.sent_at else ""
        }
        for row in rows
    ]
    emit("load_messages", messages)


@socketio.on("send_message")
def handle_send_message(data):
    tutor_id = data["tutor_id"]
    student_id = data["student_id"]
    sender = data["sender"]
    message_text = data["message"]

    message_id = uuid1()  # TIMEUUID
    sent_at = datetime.utcnow()
    query = """
            INSERT INTO messages.by_pair (tutor_id, student_id, message_id, sender_role, message_text, sent_at)
            VALUES (%s, %s, %s, %s, %s, %s) \
            """
    session_cassandra.execute(query, (tutor_id, student_id, message_id, sender, message_text, sent_at))

    room = f"{tutor_id}_{student_id}"
    emit("receive_message", {
        "sender": sender,
        "message": message_text,
        "timestamp": sent_at.isoformat()
    }, room=room)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)
