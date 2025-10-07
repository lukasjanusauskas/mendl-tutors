from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from dotenv import load_dotenv
import os


from api.tutor import (
    get_tutor_by_id,
    get_tutor_students,
    get_all_tutors,
    delete_tutor,
    create_new_tutor,
    get_tutors_by_name
)
from api.student import (
    get_students_tutors
)
from api.reviews import (
    create_review
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
    try:
        # Gauname visus studentus
        students_collection = db.student
        students_list = list(students_collection.find({}))
        
        return render_template('students.html', students=students_list)
    except Exception as e:
        return render_template('students.html', students=[], error=str(e))

from api.student import create_new_student
import re

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

@app.route('/sign-up-tutor')
def sign_up_tutor():
    try:
 
        return render_template('sign_up_tutor.html')
    except Exception as e:
        return render_template('sign_up_tutor.html', error=str(e))

@app.route('/login')
def login():
    try:
        return render_template('login.html')
    except Exception as e:
        return render_template('login.html', error=str(e))


from api.tutor import get_tutors_by_name

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

        # Išsaugoti atsiliepimą duomenų bazėje
        create_review(
            db['review'], db['tutor'], db['student'],
            review_info={
                'tutor_id': tutor_id,
                'student_id': student_id,
                'for_tutor': True,
                'review_text': review_text
            }
        )

        flash('Atsiliepimas sėkmingai pateiktas!', 'success')
        return redirect("/")
    
    return render_template('review_student.html', tutors=tutors, student_id=student_id)
# Revoke reviews



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)