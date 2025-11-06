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
        cmd.execute("SELECT * FROM login WHERE username = %s AND password = %s", (user, passw))
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
    cmd.execute("SELECT * FROM student WHERE department=%s", (dept,))
    res = cmd.fetchall()
    return render_template("admin/studentlist.html", val=res)

@app.route('/edit_student',methods=['POST','GET'])
@login_required
def edit_student():
    tlid=request.args.get('lid')
    session['slid']=tlid
    cmd.execute("SELECT * FROM student WHERE lid=%s", (tlid,))
    res=cmd.fetchone()
    return render_template("admin/student_editform.html",i=res)

@app.route('/delete_student',methods=['POST','GET'])
@login_required
def delete_student():
    tlid=request.args.get('lid')
    cmd.execute("DELETE FROM student WHERE lid=%s", (tlid,))
    con.commit()
    return '''<script>alert("Successfully Deleted");window.location='/view_student'</script>'''

@app.route('/view_subject',methods=['POST','GET'])
@login_required
def view_subject():
    return render_template("admin/subjectView.html")

@app.route('/view_subjects_dept_sem',methods=['POST','GET'])
@login_required
def view_subjects_dept_sem():
    dept=request.form['select']
    sem=request.form['select1']
    cmd.execute("SELECT `subject`.*,`teacher`.`name`,`teacher`.`teacher_code` FROM `teacher` JOIN `subject` ON `subject`.`staff_lid`=`teacher`.`lid` WHERE `subject`.`department`=%s AND `subject`.`semester`=%s", (dept, sem))
    s=cmd.fetchall()
    print(s)
    return render_template("admin/subjectView.html",val=s,dept=dept,sem=sem)

@app.route('/delete_subject',methods=['POST','GET'])
@login_required
def delete_subject():
    id=request.args.get('lid')
    cmd.execute("DELETE FROM subject WHERE sid=%s", (id,))
    con.commit()
    return '''<script>alert("Successfully Deleted");window.location='/view_subject'</script>'''

@app.route('/add_subject',methods=['POST','GET'])
@login_required
def add_subject():
    return render_template("admin/register_subject.html")

@app.route('/register_subject',methods=['POST','GET'])
@login_required
def register_subject():
    subject=request.form['text2']
    code=request.form['text1']
    dept=request.form['department']
    sem=request.form['Semester']
    staffid=request.form['Staff']
    cmd.execute("INSERT INTO subject VALUES (null, %s, %s, %s, %s, %s)", (subject, code, dept, sem, staffid))
    con.commit()
    return '''<script>alert("Successfully Registred");window.location='/view_subject'</script>'''

@app.route('/get_staff', methods=['POST'])
def get_staff():
    dept = request.form['dept']
    print(dept)
    cmd.execute("SELECT `lid`,`name`,`teacher_code` FROM `teacher` WHERE `department`=%s", (dept,))
    s = cmd.fetchall()
    print(s)

    staff_list = []
    for r in s:
        staff_list.append({
            'id': r[0],
            'name': f"{r[1]} (CODE:{r[2]})"
        })
    print(staff_list)
    resp = make_response(jsonify(staff_list))
    resp.status_code = 200
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/add_timetable',methods=['post','get'])
@login_required
def add_timetable():
    # staffid=session['lid']
    # print("SELECT `department` FROM `teacher` WHERE `lid`='"+str(staffid)+"'")
    # cmd.execute("SELECT `department` FROM `teacher` WHERE `lid`='"+str(staffid)+"'")
    # s=cmd.fetchone()
    # dept=s[0]
    # session['dept']=dept
    return render_template("admin/addtimetable.html")

@app.route('/addtimetable',methods=['post','get'])
@login_required
def addtimetable():
    dept=request.form['select']
    # subj=request.form['select1']
    sem=request.form['Semester']
    # hour=request.form['select3']
    session['semess']=sem
    session['deptt']=dept
    cmd.execute("SELECT * FROM timetable WHERE `dept`=%s AND `sem`=%s", (dept, sem))
    s=cmd.fetchone()
    if s is None:
        a1 = []
        cmd.execute("SELECT * FROM `subject` WHERE `department`=%s AND `semester`=%s", (dept, sem))
        res = cmd.fetchall()
        if res is not None:
            for i in res:
                a1.append(i[1])
            hours_per_day = 7  # Number of hours in a day
            timetable = generate_timetable(a1, hours_per_day)
            print(type(timetable))
            ll = []
            for i in timetable:
                print(i)
                # ll.append(i[1])

            print(timetable)
            result_list = [timetable[key] for key in sorted(timetable.keys())]

            # Flatten the list
            flattened_list = [item for sublist in result_list for item in sublist]

            print(flattened_list)
            cmd.execute("INSERT INTO timetable VALUES (null, %s, %s, 'Monday', %s, %s, %s, 'break', %s, %s, %s)", (dept, sem, flattened_list[0], flattened_list[1], flattened_list[2], flattened_list[4], flattened_list[5], flattened_list[6]))
            con.commit()

            cmd.execute("INSERT INTO timetable VALUES (null, %s, %s, 'Tuesday', %s, %s, %s, 'break', %s, %s, %s)", (dept, sem, flattened_list[7], flattened_list[8], flattened_list[9], flattened_list[11], flattened_list[12], flattened_list[13]))
            con.commit()

            cmd.execute("INSERT INTO timetable VALUES (null, %s, %s, 'Wednesday', %s, %s, %s, 'break', %s, %s, %s)", (dept, sem, flattened_list[14], flattened_list[15], flattened_list[16], flattened_list[18], flattened_list[19], flattened_list[20]))
            con.commit()

            cmd.execute("INSERT INTO timetable VALUES (null, %s, %s, 'Thursday', %s, %s, %s, 'break', %s, %s, %s)", (dept, sem, flattened_list[21], flattened_list[22], flattened_list[23], flattened_list[25], flattened_list[26], flattened_list[27]))
            con.commit()

            cmd.execute("INSERT INTO timetable VALUES (null, %s, %s, 'Friday', %s, %s, %s, 'break', %s, %s, %s)", (dept, sem, flattened_list[28], flattened_list[29], flattened_list[30], flattened_list[32], flattened_list[33], flattened_list[34]))
            con.commit()
            cmd.execute("SELECT `day`,`h1`,`h2`,`h3`,`h4`,`h5`,`h6`,`h7` FROM `timetable` WHERE `dept`=%s AND `sem`=%s", (dept, sem))
            res=cmd.fetchall()

            return render_template("admin/timetable.html",res=res)
        else:
            return '''<script>alert("Already Added");window.location='/viewtimetable'</script>'''
    else:
        # return '''<script>alert("Already Added");window.location='/viewtimetable'</script>'''
        return redirect('/viewtimetable')
    
def generate_timetable(subjects, hours_per_day):
    import random
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable = {}
    
    # Shuffle subjects to randomize distribution
    shuffled_subjects = subjects.copy()
    random.shuffle(shuffled_subjects)
    
    subject_index = 0
    total_subjects = len(shuffled_subjects)
    
    for day in days:
        day_schedule = []
        for hour in range(hours_per_day):
            if hour == 3:  # Break period
                day_schedule.append('Break')
            else:
                if total_subjects > 0:
                    day_schedule.append(shuffled_subjects[subject_index % total_subjects])
                    subject_index += 1
                else:
                    day_schedule.append('Free')
        timetable[day] = day_schedule
    
    return timetable


@app.route('/viewtimetable',methods=['post','get'])
@login_required
def viewtimetable():
    cmd.execute("SELECT `day`,`h1`,`h2`,`h3`,`h4`,`h5`,`h6`,`h7`,`tid` FROM `timetable` WHERE `dept`=%s AND `sem`=%s", (session['deptt'], session['semess']))
    res = cmd.fetchall()
    return render_template("admin/timetableview.html",res=res)

if __name__ == "__main__":
    app.run(debug=True)
