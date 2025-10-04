from flask import Flask, render_template
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.getenv('MONGO_URI'))
db = client['mendel-tutor']

@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/students')
def students():
    try:
        # Gauname visus studentus
        students_collection = db.student
        students_list = list(students_collection.find({}))
        
        return render_template('students.html', students=students_list)
    except Exception as e:
        return render_template('students.html', students=[], error=str(e))


if __name__ == '__main__':
    app.run(debug=True, port=5000)