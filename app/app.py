from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from dotenv import load_dotenv
import os

from api.student import (
    get_all_students,
    get_student_by_id,
    get_students_by_name,
    create_new_student,
    delete_student
)

from api.tutor import (
    get_tutor_by_id,
    get_tutor_students,
    get_all_tutors,
    delete_tutor,
    create_new_tutor,
    get_tutors_by_name
)

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"
client = MongoClient(os.getenv('MONGO_URI'))
db = client['mendel-tutor']

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/student')
def students():
    first_name = request.args.get("first_name")
    last_name = request.args.get("last_name")

    try:
        if first_name and last_name:
            students_list = get_students_by_name(db["student"], first_name, last_name)
        else:
            students_list = get_all_students(db["student"])
        return render_template("students.html", students=students_list, first_name=first_name, last_name=last_name)
    except Exception as e:
        return render_template("students.html", students=[], error=str(e))

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)