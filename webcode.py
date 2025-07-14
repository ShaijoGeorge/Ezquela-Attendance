from flask import *
import pymysql
from flask_wtf import CSRFProtect
import secrets
import functools
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key
csrf = CSRFProtect(app)  # Enable CSRF protection

def get_db_connection():
    return pymysql.connect(host='localhost', port=3306, user='root', passwd='', db='attendance_face')
con = get_db_connection()
cmd = con.cursor()

def login_required(func):
    @functools.wraps(func)
    def secure_function():
        if "lid" not in session:
            return index()
        return func()
    return secure_function

def get_user_role(user_id):
    cmd.execute("SELECT usertype FROM login WHERE id = %s", (user_id,))
    result = cmd.fetchone()
    if result:
        return result[0]
    else:
        return None

@app.route('/')
def index():
    if 'lid' in session:
        role = get_user_role(session['lid'])
        if role == "admin":
            return redirect('/admin_home')
        elif role == "teacher":
            return redirect('/teacher_home')
        elif role == "student":
            return redirect('/student_home')
    else:
        return redirect(url_for('user'))

@app.route('/login', methods=["GET", "POST"])
def user():
    if 'lid' in session:
        return redirect(url_for('index'))
    if request.method == "POST":
        user = request.form['textfield']
        passw = request.form['textfield2']
        cmd.execute("select*from login where username='"+user+"' and password='"+passw+"'")
        result = cmd.fetchone()
        if result is None:
            return '''<script>alert("invalid username and password");window.location='/login'</script>'''
        else:
            session['lid'] = result[0]
        if 'lid' in session:
            role = get_user_role(session['lid'])
            if role == "admin":
                return redirect('/admin_home')
            elif role == "teacher":
                return redirect('/teacher_home')
            elif role == "student":
                return redirect('/student_home')
        else:
            return redirect(url_for('user'))

    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/logout')
def logout():
    print("lllllllllllllllllllll")
    session.pop('lid', None)
    return redirect(url_for('user'))

@app.route('/student_signup',methods=['post','get'])
def student_signup():
    return render_template("student.html")

@app.route('/add_student',methods=['post','get'])
def add_student():
    try:
        # Get form data
        fname=request.form['text1']
        regno=request.form['text2']
        address=request.form['text3']
        phone=request.form['text4']
        email=request.form['text5']

        dob=request.form['text6']
        dept=request.form['select']
        Semester=request.form['select1']
        division=request.form['select3']
        guardian=request.form['guardian']
        guardian_phone=request.form['phone']

        # Handle file upload
        if 'files' not in request.files:
            return '''<script>alert("No file uploaded");window.location='/student_signup'</script>'''
            
        img = request.files['files']
        if img.filename == '':
            return '''<script>alert("No selected file");window.location='/student_signup'</script>'''

        # Generate unique filename
        filename = secure_filename(img.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        upload_path = os.path.join('./static/photos/studentphoto', unique_filename)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        img.save(upload_path)

        uname = request.form['uname']
        password = request.form['password']
        cnfpassword = request.form['cnfpassword']
        
        if password != cnfpassword:
            return '''<script>alert("Password Mismatch!");window.location='/student_signup'</script>'''

        # Database operations
        with con.cursor() as cmd:
            cmd.execute("INSERT INTO login VALUES (null, %s, %s, 'student')", (uname, password))
            id = con.insert_id()
            cmd.execute("""INSERT INTO student VALUES (null, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (id, fname, regno, address, phone, email, dob, dept, Semester, division, unique_filename, guardian, guardian_phone))
            con.commit()
            
        return '''<script>alert("Successfully Registered");window.location='/'</script>'''
        
    except Exception as e:
        print(f"Error: {str(e)}")
        # Rollback in case of error
        if 'con' in locals():
            con.rollback()
        return f'''<script>alert("Registration failed: {str(e)}");window.location='/student_signup'</script>'''

if __name__ == "__main__":
    app.run(debug=True)