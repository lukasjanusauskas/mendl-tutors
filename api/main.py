from flask import Flask, jsonify, request
from connection import get_db
from tutor import (
    create_new_tutor
)

db = get_db()
app = Flask(__name__)

@app.route('/tutor/', methods = ['POST'])
def home():
    try:
        insert_result = create_new_tutor(
            tutor_collection=db['tutor'],
            tutor_info=request.args
        )

    except ValueError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except KeyError as err:
        return jsonify({'server_response': f'{err}'}), 400
    except TypeError as err:
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


if __name__ == '__main__':

    app.run(host = '0.0.0.0', debug = True)

    db.close()
