from flask import *
import pymysql
from flask_wtf import CSRFProtect
import secrets
import functools
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import time

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

@app.route('/admin_home', methods=['POST', 'GET'])
@login_required
def admin_home():
    get_user_role(session['lid'])
    return render_template('admin/base.html')

@app.route('/view_staff', methods=['POST', 'GET'])
@login_required
def view_staff():
    cmd = con.cursor()
    cmd.execute("SELECT * FROM teacher")
    res = cmd.fetchall()
    return render_template("admin/stafflist.html", val=res)

@app.route('/delete_staff', methods=['POST', 'GET'])
@login_required
def delete_staff():
    tlid = request.args.get('lid')
    cmd = con.cursor()
    cmd.execute("DELETE FROM teacher WHERE lid=%s", (tlid,))
    con.commit()
    return '''<script>alert("Successfully Deleted");window.location='/view_staff'</script>'''

@app.route('/add_staff', methods=['POST', 'GET'])
@login_required
def add_staff():
    return render_template("admin/staff_form.html")

@app.route('/staffreg', methods=['POST', 'GET'])
@login_required
def staffreg():
    try:
        fname = request.form['text1']
        code = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        qualification = request.form['text6']
        dept = request.form['select']
        img = request.files['files']
        name = secure_filename(img.filename)
        import time
        req = time.strftime("%Y%m%d_%H%M%S") + ".jpg"
        img.save(os.path.join('./static/photos/staffphoto', req))
        uname = request.form['uname']
        password = request.form['password']
        cnfpassword = request.form['cnfpassword']
        if password == cnfpassword:
            cmd = con.cursor()
            cmd.execute("INSERT INTO login VALUES (null, %s, %s, 'teacher')", (uname, password))
            id = con.insert_id()
            cmd.execute("INSERT INTO teacher VALUES (null, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (id, fname, code, address, phone, email, qualification, dept, req))
            con.commit()
            return '''<script>alert("Successfully Added");window.location='/view_staff'</script>'''
        else:
            return '''<script>alert("Password Mismatch!");window.location='/add_staff'</script>'''
    except Exception as e:
        print(e)
        return '''<script>alert("Error occurred");window.location='/add_staff'</script>'''

@app.route('/edit_staff', methods=['POST', 'GET'])
def edit_staff():
    cmd = con.cursor()
    cmd.execute("SELECT * FROM teacher WHERE lid=%s", (request.args.get('lid'),))
    res = cmd.fetchone()
    cmd.execute("SELECT dept FROM department")
    dept = cmd.fetchall()
    return render_template("admin/staff_form.html", val=res, dept=dept)

@app.route('/update_staff', methods=['POST', 'GET'])
def update_staff():
    try:
        fname = request.form['text1']
        code = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        qualification = request.form['text6']
        dept = request.form['select']
        lid = request.form['lid']
        img = request.files['files']
        if img:
            name = secure_filename(img.filename)
            import time
            req = time.strftime("%Y%m%d_%H%M%S") + ".jpg"
            img.save(os.path.join('./static/photos/staffphoto', req))
            cmd = con.cursor()
            cmd.execute("UPDATE teacher SET name=%s, teacher_code=%s, address=%s, phone=%s, email=%s, qualification=%s, department=%s, photo=%s WHERE lid=%s", (fname, code, address, phone, email, qualification, dept, req, lid))
            con.commit()
        else:
            cmd = con.cursor()
            cmd.execute("UPDATE teacher SET name=%s, teacher_code=%s, address=%s, phone=%s, email=%s, qualification=%s, department=%s WHERE lid=%s", (fname, code, address, phone, email, qualification, dept, lid))
            con.commit()
        return '''<script>alert("Successfully Updated");window.location='/view_staff'</script>'''
    except Exception as e:
        print(e)
        return '''<script>alert("Error occurred");window.location='/edit_staff'</script>'''

@app.route('/view_student', methods=['POST', 'GET'])
@login_required
def view_student():
    cmd = con.cursor()
    cmd.execute("SELECT * FROM student")
    res = cmd.fetchall()
    return render_template("admin/studentlist.html", val=res)

@app.route('/dept_search_student', methods=['POST', 'GET'])
@login_required
def dept_search_student():
    dept = request.form['select']
    cmd = con.cursor()
    cmd.execute("SELECT * FROM student WHERE department='"+dept+"'")
    res = cmd.fetchall()
    return render_template("admin/studentlist.html", val=res)

@app.route('/edit_student',methods=['post','get'])
@login_required
def edit_student():
    tlid=request.args.get('lid')
    session['slid']=tlid
    cmd.execute("select * from student where lid='"+tlid+"'")
    res=cmd.fetchone()
    return render_template("admin/student_editform.html",i=res)

@app.route('/delete_student',methods=['post','get'])
@login_required
def delete_student():
    tlid=request.args.get('lid')
    cmd.execute("delete from student where lid='"+tlid+"' ")
    con.commit()
    return '''<script>alert("Successfully Deleted");window.location='/view_student'</script>'''

if __name__ == "__main__":
    app.run(debug=True)