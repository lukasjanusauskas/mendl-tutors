from flask import Flask, jsonify, request
from bson.errors import InvalidId
from connection import get_db
from tutor import (
    create_new_tutor,
    get_all_tutors,
    get_tutor_by_id,
    get_tutors_by_name,
    assign_student_to_tutor,
    get_tutor_students,
    delete_tutor,
    remove_student_from_tutor
    #get_tutor_pagal_dal_ir_kalse
)
from student import (
    create_new_student,
    get_all_students,
    get_student_by_id,
    get_students_by_name,
    delete_student
)

db = get_db()
app = Flask(__name__)

#--------------TUTOR API--------------------------------------
@app.route('/tutor/', methods = ['POST'])
def add_new_tutor():
    try:
        insert_result = create_new_tutor(
            tutor_collection=db['tutor'],
            tutor_info=request.get_json()
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except KeyError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except Exception as err:
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

    if insert_result.acknowledged:
        output = jsonify({
            'server_response': 'pavyko',
            'tutor_id': str( insert_result.inserted_id )
        })

        return output, 200

    else:
        output = jsonify({
            'server_response': 'nepavyko'
        })

        return output, 400

@app.route("/tutor/assign_student/", methods=["POST"])
def assign_student():
    """
    Priskirti studenta korepetitoriui pagal email ir subject.
    Laukiamas JSON su tutor_id, student_id ir subject.
    """
    try:
        data = request.get_json()

        # Tikriname ar visi reikalingi laukai yra
        required_fields = ["tutor_id", "student_id", "subject"]
        for field in required_fields:
            if field not in data:
                return jsonify({"server_response": f"Trūksta {field}"}), 400

        result = assign_student_to_tutor(
            tutor_collection=db["tutor"],
            student_collection=db["student"],
            tutor_id=data["tutor_id"],
            student_id=data["student_id"],
            subject=data["subject"]
        )

        if result.modified_count > 0:
            return jsonify({
                "server_response": "Studentas priskirtas sėkmingai",
                "tutor_id": data["tutor_id"],
                "student_id": data["student_id"],
                "subject": data["subject"]
            }), 200
        else:
            return jsonify({"server_response": "Nėra pakeitimų (gal jau priskirtas?)"}), 200

    except InvalidId:
        return jsonify({"server_response": "Blogas student_id formatas"}), 400
    except ValueError as e:
        return jsonify({"server_response": str(e)}), 400
    except Exception as e:
        return jsonify({"server_response": f"Serverio klaida: {e}"}), 500

@app.route("/tutor/<tutor_id>/students", methods=["GET"])
def tutor_students(tutor_id: str):
    try:
        students = get_tutor_students(
            tutor_collection=db["tutor"],
            student_collection=db["student"],
            tutor_id=tutor_id
        )
        return jsonify({
            "tutor_id": tutor_id,
            "students": students
        }), 200

    except ValueError as e:
        return jsonify({"server_response": str(e)}), 404
    except Exception as e:
        return jsonify({"server_response": f"Serverio klaida: {e}"}), 500

@app.route("/tutor/<string:tutor_id>", methods=["GET"])
def api_get_tutor(tutor_id):
    """API endpointas gauti vieną korepetitorių pagal ID."""
    tutor = get_tutor_by_id(db["tutor"], tutor_id)
    if not tutor:
        return jsonify({"error": "Korepetitorius nerastas"}), 404
    return jsonify(tutor), 200

@app.route("/tutors", methods=["GET"])
def api_get_tutors():
    """API endpointas gauti visus korepetitorius arba ieškoti pagal vardą/pavardę."""
    name = request.args.get("name")
    if name:
        return jsonify(get_tutors_by_name(db["tutor"], name)), 200
    return jsonify(get_all_tutors(db["tutor"])), 200

@app.route("/tutor/<tutor_id>", methods=["DELETE"])
def remove_tutor(tutor_id: str):
    try:
        result = delete_tutor(db["tutor"], tutor_id)
        if result["deleted"]:
            return jsonify({"server_response": "Korepetitorius ištrintas"}), 200
        else:
            return jsonify({"server_response": "Korepetitorius nerastas"}), 404
    except Exception as e:
        return jsonify({"server_response": f"Serverio klaida: {e}"}), 500

@app.route("/tutor/<tutor_id>/students/<student_id>", methods=["DELETE"])
def tutor_remove_student(tutor_id: str, student_id: str):
    try:
        result = remove_student_from_tutor(
            tutor_collection=db["tutor"],
            tutor_id=tutor_id,
            student_id=student_id
        )

        if result["removed"]:
            return jsonify({"server_response": "Studentas pašalintas"}), 200
        else:
            return jsonify({"server_response": "Studentas nerastas pas korepetitorių"}), 404

    except Exception as e:
        return jsonify({"server_response": f"Serverio klaida: {e}"}), 500
#-------------------STUDENT API--------------------------

# @app.route("/student/", methods=["POST"])
# def add_student():
#     try:
#         insert_result = create_new_student(
#             student_collection=db['student'],
#             student_info=request.get_json()
#         )
#     except ValueError as ve:
#         return jsonify({"error": str(ve)}), 400
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

#     if insert_result.acknowledged:
#         return jsonify({
#             "message": "Student added successfully",
#             "student_id": str(insert_result.inserted_id)
#         }), 201
#     else:
#         return jsonify({"message": "Nepavyko pridėti studento"}), 400

# @app.route("/student/<string:student_id>", methods=["GET"])
# def api_get_student(student_id):
#     """API endpointas gauti vieną studentą pagal ID."""
#     student = get_student_by_id(db["student"], student_id)
#     if not student:
#         return jsonify({"error": "Studentas nerastas"}), 404
#     return jsonify(student), 200

# @app.route("/students", methods=["GET"])
# def api_get_students():
#     """API endpointas gauti visus studentus arba ieškoti pagal vardą/pavardę."""
#     name = request.args.get("name")
#     if name:
#         return jsonify(get_students_by_name(db["student"], name)), 200
#     return jsonify(get_all_students(db["student"])), 200

# @app.route("/student/<student_id>", methods=["DELETE"])
# def remove_student(student_id: str):
#     try:
#         result = delete_student(db["student"], db["tutor"], student_id)
#         if result["deleted"]:
#             return jsonify({"server_response": "Studentas ištrintas ir pašalintas iš korepetitorių"}), 200
#         else:
#             return jsonify({"server_response": "Studentas nerastas"}), 404
#     except Exception as e:
#         return jsonify({"server_response": f"Serverio klaida: {e}"}), 500



if __name__ == '__main__':

    app.run(host = '0.0.0.0', debug = True)

    db.close()
