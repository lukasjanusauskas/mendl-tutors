from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from dotenv import load_dotenv
import hashlib
import os
import re

from api.tutor import (
    get_tutor_by_id,
    get_tutor_students,
    get_all_tutors,
    delete_tutor,
    create_new_tutor,
    get_tutors_by_name
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

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"
client = MongoClient(os.getenv('MONGO_URI'))
db = client['mendel-tutor']

@app.route("/")
def index():
    return render_template("index.html")


@app.route('/students')
def students():
    first_name = request.args.get("first_name")
    last_name = request.args.get("last_name")

    if first_name and last_name:
        students_list = get_students_by_name(db["student"], first_name, last_name)
    else:
        students_list = get_all_students(db["student"])


    if first_name is None:
        return render_template("students.html", students=students_list, first_name="Vardas", last_name="Pavardė")

    elif first_name is not None:
        return render_template("students.html", students=students_list, first_name=first_name, last_name=last_name)


@app.route("/student/<student_id>")
def view_student(student_id):
    try:
        student = get_student_by_id(db["student"], student_id)
        tutors = []

        tutors_cursor = db.tutor.find({"students_subjects.student.student_id": student_id})

        for t in tutors_cursor:
            tutors.append({
                "first_name": t.get("first_name", ""),
                "last_name": t.get("last_name", ""),
                "email": t.get("email", ""),
                "subject": ", ".join(
                    [s.get("subject", "") for s in t.get("subjects", [])]
                )
            })
        return render_template("student.html", student=student, tutors=tutors)
    except Exception as e:
        return render_template("student.html", student=None, tutors=None, error=str(e))


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

            if "student_email" in request.form:
                data["student_email"] = request.form["student_email"]

            create_new_student(db.student, data)
            flash("Mokinys sėkmingai pridėtas!", "success")
            return redirect(url_for("students"))

        except Exception as e:
            flash(str(e), "danger")

    return render_template("add_student.html")


@app.route("/student/<student_id>/delete", methods=["GET", "POST"])
def delete_student_ui(student_id):
    try:
        result = delete_student(db.student, db.tutor, student_id)
        if result["deleted"]:
            flash("Mokinys sėkmingai ištrintas!", "success")
        else:
            flash("Mokinys nerastas.", "warning")

    except Exception as e:
            flash(str(e), "danger")

    return redirect(url_for("students"))


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
                    raise ValueError(f"Neteisingas telefono numerio formatas: '{phone}'. Telefono numeris turi būti 7-15 skaitmenų, gali prasidėti '+' ženklu")
            
            # Validate student phone number if provided
            student_phone = request.form.get('phone_number', '').strip()
            if student_phone and not re.match(phone_pattern, student_phone):
                raise ValueError(f"Neteisingas mokinio telefono numerio formatas: '{student_phone}'. Telefono numeris turi būti 7-15 skaitmenų, gali prasidėti '+' ženklu")

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
            create_new_student(db.student, student_info)
            flash('Studentas sėkmingai užregistruotas!', 'success')
            return redirect(url_for('students'))

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

            # Subjects apdorojimas - konvertuojame į objektų masyvą
            subjects_raw = request.form.get('subjects', "")
            if subjects_raw:
                subjects_list = [s.strip() for s in subjects_raw.split(",") if s.strip()]
                tutor_info['subjects'] = [{"subject": s, "max_class": 12} for s in subjects_list]
            else:
                raise ValueError("Būtina nurodyti bent vieną dėstomą dalyką")

            create_new_tutor(db.tutor, tutor_info)
            flash("Korepetitorius sėkmingai užregistruotas!", "success")
            return redirect(url_for("tutors"))
        except Exception as e:
            return render_template('sign_up_tutor.html', error=str(e))
    
    # GET request
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
                # Verify password
                password_encoded = password.encode('utf-8')
                hash_algo = hashlib.sha256()
                hash_algo.update(password_encoded)
                hashed_password = hash_algo.hexdigest()
                
                if tutor.get('password_hashed') == hashed_password:
                    session['user_id'] = str(tutor['_id'])
                    session['user_type'] = 'tutor'
                    session['user_name'] = f"{tutor['first_name']} {tutor['last_name']}"
                    flash('Sėkmingai prisijungėte!', 'success')
                    return redirect(url_for('view_tutor', tutor_id=str(tutor['_id'])))
            
            # Check if user is a student
            student = db.student.find_one({"student_email": email})
            if student:
                # Verify password
                password_encoded = password.encode('utf-8')
                hash_algo = hashlib.sha256()
                hash_algo.update(password_encoded)
                hashed_password = hash_algo.hexdigest()
                
                if student.get('password_hashed') == hashed_password:
                    session['user_id'] = str(student['_id'])
                    session['user_type'] = 'student'
                    session['user_name'] = f"{student['first_name']} {student['last_name']}"
                    flash('Sėkmingai prisijungėte!', 'success')
                    return redirect(url_for('view_student', student_id=str(student['_id'])))
            
            # If we get here, login failed
            return render_template('login.html', error='Neteisingas el. paštas arba slaptažodis')
            
        except Exception as e:
            return render_template('login.html', error=str(e))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sėkmingai atsijungėte!', 'info')
    return redirect(url_for('index'))

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
            tutors_list = list(tutor_collection.find({}))

        return render_template(
            "tutors.html",
            tutors=tutors_list,
            first_name=first_name,
            last_name=last_name
        )

    except Exception as e:
        return render_template("tutors.html", tutors=[], error=str(e))



@app.route("/tutor/<tutor_id>/view")
def view_tutor(tutor_id):
    try:
        tutor = get_tutor_by_id(db.tutor, tutor_id)
        if not tutor:
            return render_template("tutor.html", tutor=None, students=None)

        students = get_tutor_students(db.tutor, tutor_id)
        return render_template("tutor.html", tutor=tutor, students=students)

    except Exception as e:
        return render_template("tutor.html", tutor=None, students=None, error=str(e))

@app.route("/tutors/<tutor_id>/delete", methods=["GET", "POST"])
def remove_tutor(tutor_id):
    try:
        result = delete_tutor(db.tutor, tutor_id)
        if result["deleted"]:
            flash("Korepetitorius sėkmingai ištrintas!", "success")
        else:
            flash("Korepetitorius nerastas.", "warning")
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

            # Необязательные поля
            second_name = request.form.get('second_name')
            if second_name:
                tutor_info['second_name'] = second_name

            phone = request.form.get('phone_number')
            if phone:
                tutor_info['phone_number'] = phone

            subjects_raw = request.form.get('subjects', "")
            if subjects_raw:
                subjects_list = [s.strip() for s in subjects_raw.split(",") if s.strip()]
                tutor_info['subjects'] = [{"subject": s, "max_class": 12} for s in subjects_list]

            create_new_tutor(db.tutor, tutor_info)
            flash("Korepetitorius sėkmingai pridėtas!", "success")
            return redirect(url_for("tutors"))
        except Exception as e:
            flash(str(e), "danger")

    return render_template("add_tutor.html")

@app.route('/tutor/<tutor_id>/create_review', methods=['GET', 'POST'])
def add_new_review_tutor(tutor_id):
    # Gauti mokinius is duombzes 
    students = get_tutor_students(db['tutor'], tutor_id)

    students = {stud['student_id']: f"{stud['first_name']} {stud['last_name']}"
                for stud in students}

    # Jei nera mokiniui -> flashcard
    if not students:
        flash('Jūs neturite mokinių', 'warning')
        return redirect("/")

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        review_text = request.form.get('review_text')

        # Išsaugoti atsiliepimą duomenų bazėje
        create_review(
            db['review'], db['tutor'], db['student'],
            review_info={
                'tutor_id': tutor_id,
                'student_id': student_id,
                'for_tutor': False,
                'review_text': review_text
            }
        )

        flash('Atsiliepimas sėkmingai pateiktas!', 'success')
        return redirect(url_for('view_tutor', tutor_id=tutor_id))
    
    return render_template('review_tutor.html', students=students, tutor_id=tutor_id)


@app.route('/student/<student_id>/create_review', methods=['GET', 'POST'])
def add_new_review_student(student_id):
    # Gauti mokinius is duombzes 

    try:
        tutors = get_students_tutors(db['tutor'], student_id)
    except AssertionError:
        flash('Jūs neturite priskirtų mokytojų', 'warning')
        return redirect("/")

    tutors = {tut['_id']: f"{tut['first_name']} {tut['last_name']}"
                for tut in tutors}

    # Jei nera mokytoju -> flashcard
    if not students:
        flash('Jūs neturite priskirtų mokytojų', 'warning')
        return redirect(url_for('view_tutor', tutor_id=tutor_id))

    if request.method == 'POST':
        tutor_id = request.form.get('tutor_id')
        review_text = request.form.get('review_text')
        rating = request.form.get('rating')

        # Išsaugoti atsiliepimą duomenų bazėje
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

        flash('Atsiliepimas sėkmingai pateiktas!', 'success')
        return redirect("/")
    
    return render_template('review_student.html', tutors=tutors, student_id=student_id)


@app.route('/tutor/<tutor_id>/review_list', methods=['GET'])
def show_reviews_tutor(tutor_id):

    recieved_reviews, written_reviews = list_reviews_tutor(db['review'], tutor_id)
    
    return render_template('review_view.html',
                           tutor_id=tutor_id,
                           written_reviews=written_reviews,
                           recieved_reviews=recieved_reviews)


@app.route('/student/<student_id>/review_list', methods=['GET'])
def show_reviews_student(student_id):

    recieved_reviews, written_reviews = list_reviews_student(db['review'], student_id)

    return render_template('review_view_student.html',
                           student_id=student_id,
                           written_reviews=written_reviews,
                           recieved_reviews=recieved_reviews)


@app.route('/tutor/revoke_review/<tutor_id>/<review_id>', methods=['GET'])
def tutor_revoke_review(tutor_id, review_id):

    try:
        revoke_review(db['review'], review_id)
    except Exception as err:
        flash(str(err), 'danger')

    flash('Sėkmingai atsiimtas atsiliepimas', 'success')

    return redirect(url_for('show_reviews_tutor', tutor_id=tutor_id))


@app.route('/student/revoke_review/<student_id>/<review_id>', methods=['GET'])
def student_revoke_review(student_id, review_id):

    try:
        revoke_review(db['review'], review_id)
    except Exception as err:
        flash(str(err), 'danger')

    flash('Sėkmingai atsiimtas atsiliepimas', 'success')

    return redirect(url_for('show_reviews_student', student_id=student_id))


@app.route('/review/revoke/tutor/<review_id>/<tutor_id>', methods=['GET'])
def revoke_review_dialog_tutor(review_id, tutor_id):
    """ View and (optionally) revoke review"""

    try:
        review = get_single_review(db['review'], review_id=review_id)

    except ValueError:
        flash('Could not find review', 'danger')
        redirect( url_for('show_reviews_tutor', tutor_id=tutor_id) )

    return render_template('revoke_review.html',
                           review=review,
                           review_id=review_id,
                           tutor_id=tutor_id)


@app.route('/review/revoke/student/<review_id>/<student_id>', methods=['GET'])
def revoke_review_dialog_student(review_id, student_id):
    """ View and (optionally) revoke review"""

    try:
        review = get_single_review(db['review'], review_id=review_id)

    except ValueError:
        flash('Could not find review', 'danger')
        redirect( url_for('show_reviews_student', tutor_id=student_id) )

    return render_template('revoke_review_student.html',
                           review=review,
                           review_id=review_id,
                           student_id=student_id)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)