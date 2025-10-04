from flask import Flask, jsonify, request
from bson.errors import InvalidId
from connection import get_db
import traceback

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
from lesson import (
    create_lesson,
    add_student_to_lesson,
    change_lesson_date,
    delete_lesson,
    list_lessons_tutor_week,
    list_lessons_tutor_month,
    list_lessons_student_week,
    list_lesson_student_month,
    delete_student_from_lesson,
    change_lesson_price_student,
    change_lesson_time_student
)
from reviews import (
    create_review,
    revoke_review,
    list_reviews_tutor,
    list_reviews_student
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

@app.route("/student/", methods=["POST"])
def add_student():
    try:
        insert_result = create_new_student(
            student_collection=db['student'],
            student_info=request.get_json()
        )
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if insert_result.acknowledged:
        return jsonify({
            "message": "Student added successfully",
            "student_id": str(insert_result.inserted_id)
        }), 201
    else:
        return jsonify({"message": "Nepavyko pridėti studento"}), 400

@app.route("/student/<string:student_id>", methods=["GET"])
def api_get_student(student_id):
    """API endpointas gauti vieną studentą pagal ID."""
    student = get_student_by_id(db["student"], student_id)
    if not student:
        return jsonify({"error": "Studentas nerastas"}), 404
    return jsonify(student), 200

@app.route("/students", methods=["GET"])
def api_get_students():
    """API endpointas gauti visus studentus arba ieškoti pagal vardą/pavardę."""

    first_name = request.args.get("first_name")
    last_name = request.args.get("last_name")

    if first_name and last_name:
        return jsonify(get_students_by_name(db["student"], first_name, last_name)), 200

    # Jei pateiktas first_name, bet ne last_name
    elif first_name:
        all_students = get_all_students(db["student"])
        msg = {'server_msg': 'Pateikete full_name, reikia ir last_name'}

        all_students = [student | msg for student in all_students]
        return jsonify(all_students), 206

    # Jei pateiktas last_name, bet ne first_name
    elif last_name:
        all_students = get_all_students(db["student"])
        msg = {'server_msg': 'Pateikete last_name, reikia ir first_name'}

        all_students = [student | msg for student in all_students]
        return jsonify(all_students), 206

    return jsonify(get_all_students(db["student"])), 200

@app.route("/student/<student_id>", methods=["DELETE"])
def remove_student(student_id: str):
    try:
        result = delete_student(db["student"], db["tutor"], student_id)
        if result["deleted"]:
            return jsonify({"server_response": "Studentas ištrintas ir pašalintas iš korepetitorių"}), 200
        else:
            return jsonify({"server_response": "Studentas nerastas"}), 404
    except Exception as e:
        return jsonify({"server_response": f"Serverio klaida: {e}"}), 500

#-------------------LESSON API--------------------------
@app.route("/lesson/", methods=["POST"])
def add_new_lesson():
    try:
        insert_result = create_lesson(
            lesson_collection=db['lesson'],
            tutor_collection=db['tutor'],
            student_collection=db['student'],
            lesson_info=request.get_json()
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
            'lesson_id': str( insert_result.inserted_id )
        })

        return output, 200

    else:
        output = jsonify({'server_response': 'nepavyko'})

        return output, 400


@app.route("/lesson/delete_lesson/<lesson_id>", methods=["DELETE"])
def delete_lesson_by_id(lesson_id):
    """ Delete lesson -> pakeisti tipa i pakeista, kadangi isimti pilnai nenorim del ateities konfliktu. """
    
    update_result = delete_lesson(db['lesson'], lesson_id)
    if update_result is not None:
        return jsonify({'server_response': 'Pakeistas pamokos statusas'}), 200
 
    else:
        return jsonify({'server_response': 'Pamoka negalejo buti istrinta, nes ji jau istrinta'})


@app.route("/lesson/add_student/<lesson_id>/<student_id>", methods=["POST"])
def add_studdent_lesson(lesson_id: str, student_id: str):
    try:
        update_result = add_student_to_lesson(
            db['lesson'], 
            db['student'],
            lesson_id,
            student_id
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400

    if update_result is not None:
        output = jsonify({
            'server_response': 'Mokinys pridetas',
        })

        return output, 200
    
    else:
        return jsonify({'server_response': 'nepavyko'}), 400


@app.route("/lesson/change_time/<lesson_id>/<time>", methods=["POST"])
def change_lesson_time(lesson_id: str, time: str):
    try:
        update_result = change_lesson_date(db['lesson'], lesson_id, time)
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400

    if update_result is not None:
        output = jsonify({
            'server_response': 'pamoka_atnaujinta',
            'time': time
        })

        return output, 200

    else:
        return jsonify({'server_response': 'nepavyko'}), 400


@app.route("/lesson/tutor/<tutor_id>", methods=["GET"])
def list_active_lessons_week_tutor(tutor_id: str):
    try:
        read_result = list_lessons_tutor_week(db['lesson'], db['tutor'], tutor_id)
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400

    if read_result is not None:
        return read_result, 200

    else:
        return jsonify({'server_response': 'nepavyko'}), 400


@app.route("/lesson/tutor/<tutor_id>/<year>/<month>", methods=["GET"])
def list_all_lessons_month_tutor(tutor_id: str, year: int, month: int):
    try:
        read_result = list_lessons_tutor_month(
            db['lesson'], 
            db['tutor'], 
            tutor_id = tutor_id,
            year = year,
            month = month
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400

    if read_result is not None:
        return read_result, 200

    else:
        return jsonify({'server_response': 'nepavyko'}), 400


@app.route("/lesson/student/<student_id>", methods=["GET"])
def list_active_lessons_week_student(student_id: str):
    try:
        read_result = list_lessons_student_week(
            db['lesson'], db['student'], student_id
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400

    if read_result is not None:
        return read_result, 200

    else:
        return jsonify({'server_response': 'nepavyko'}), 400


@app.route("/lesson/student/<student_id>/<year>/<month>", methods=["GET"])
def list_all_lessons_month_student(student_id: str, year: int, month: int):
    try:
        read_result = list_lesson_student_month(
            db['lesson'], 
            db['student'], 
            student_id = student_id,
            year = year,
            month = month
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400

    if read_result is not None:
        return read_result, 200

    else:
        return jsonify({'server_response': 'nepavyko'}), 400


@app.route("/lesson/<lesson_id>/student/<student_id>/change_price/<float:price>", methods=["POST"])
def change_lesson_information_price(lesson_id: str, student_id: str, price: float):
    try:
        update_result = change_lesson_price_student(
            db['lesson'],
            lesson_id=lesson_id,
            student_id=student_id,
            price=price
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except Exception as err:
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

    if update_result is not None:
        output = jsonify({
            'server_response': 'Pavyko padaryti pakeitima',
        })

        return output, 200

    else:
        output = jsonify({
            'server_response': 'nepavyko'
        })

        return output, 400


@app.route("/lesson/remove_student/<lesson_id>/<student_id>", methods=["DELETE"])
def remove_student_from_lesson(lesson_id: str, student_id: str):
    update_result = delete_student_from_lesson(
        db['lesson'], db['student'], lesson_id, student_id
    )

    if update_result is not None:
        output = jsonify({'server_response': 'Pavyko padaryti pakeitima'})
        return output, 200
    
    else:
        output = jsonify({'server_response': 'nepavyko'})
        return output, 400


@app.route("/lesson/change_time_student", methods=["POST"])
def change_student_lesson_time():
    try:
        update_result = change_lesson_time_student(
            db['lesson'], db['tutor'], db['student'],
            lesson_info=request.get_json()
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except KeyError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

    if update_result:
        output = jsonify({'server_response': 'pavyko',})
        return output, 200

    else:
        output = jsonify({'server_response': 'nepavyko'})
        return output, 400

#-------------------LESSON API--------------------------

@app.route('/review/tutor', methods = ['POST'])
def add_review_tutor():
    """ Leave a review for a student. Tutor - reviews > student. """
    try:
        review_info = request.get_json() | {'for_tutor': False}

        insert_result = create_review(
            review_collection=db['review'],
            tutor_collection=db['tutor'],
            student_collection=db['student'],
            review_info=review_info
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except KeyError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

    if insert_result.acknowledged:
        output = jsonify({
            'server_response': 'pavyko',
            'lesson_id': str( insert_result.inserted_id )
        })

        return output, 200

    else:
        output = jsonify({'server_response': 'nepavyko'})

        return output, 400


@app.route('/review/student', methods = ['POST'])
def add_review_student():
    """ Leave a review for a tutor. Student (parents) - reviews > tutor. """
    try:
        review_info = request.get_json() | {'for_tutor': True}

        insert_result = create_review(
            review_collection=db['review'],
            tutor_collection=db['tutor'],
            student_collection=db['student'],
            review_info=review_info
        )
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except KeyError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

    if insert_result.acknowledged:
        output = jsonify({
            'server_response': 'pavyko',
            'lesson_id': str( insert_result.inserted_id )
        })

        return output, 200

    else:
        output = jsonify({'server_response': 'nepavyko'})

        return output, 400


@app.route('/review/<review_id>', methods = ['DELETE'])
def remove_review(review_id: str):
    try: 
        revoked_review = revoke_review(db['review'], review_id)
    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

    if revoked_review:
        output = jsonify({'server_response': 'pavyko'})
        return output, 200

    else:
        output = jsonify({'server_response': 'nepavyko'})
        return output, 400


@app.route('/review/tutor/<tutor_id>', methods = ['GET'])
def list_reviews_for_tutor(tutor_id: str):
    try: 
        reviews = list_reviews_tutor(
            db['review'], tutor_id, filter_revoked=True
        )

    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

        
    output = jsonify({'reviews': reviews})
    return output, 200


@app.route('/review/student/<student_id>', methods = ['GET'])
def list_reviews_for_student(student_id: str):
    try: 
        reviews = list_reviews_student(
            db['review'], student_id, filter_revoked=True
        )

    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

        
    output = jsonify({'reviews': reviews})
    return output, 200


@app.route('/review/tutor/all/<tutor_id>', methods = ['GET'])
def list_reviews_for_tutor_all(tutor_id: str):
    try: 
        reviews = list_reviews_tutor(
            db['review'], tutor_id, filter_revoked=False
        )

    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

        
    output = jsonify({'reviews': reviews})
    return output, 200


@app.route('/review/student/all/<student_id>', methods = ['GET'])
def list_reviews_for_student_all(student_id: str):
    try: 
        reviews = list_reviews_student(
            db['review'], student_id, filter_revoked=False
        )

    except Exception as err:
        traceback.print_exc()
        return jsonify({'server_response': f'Serverio klaida: {err}'}), 500

        
    output = jsonify({'reviews': reviews})
    return output, 200


if __name__ == '__main__':

    app.run(host = '0.0.0.0', debug = True)

    db.close()
