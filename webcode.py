from flask import *
import pymysql

app = Flask(__name__)
app.secret_key = "qwe23"

def get_db_connection():
    return pymysql.connect(host='localhost', port=3306, user='root', passwd='', db='attendance_face')
con = get_db_connection()

@app.route('/')
def index():
    return "Welcome to Ezquela Attendance System"

if __name__ == "__main__":
    app.run(debug=True)