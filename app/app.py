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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)