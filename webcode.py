from flask import *
import pymysql
from flask_wtf import CSRFProtect
import secrets
import functools
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from dbutils.pooled_db import PooledDB

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
csrf = CSRFProtect(app)

# Database connection pool configuration
pool = PooledDB(
    creator=pymysql,  # Database module
    maxconnections=10,  # Max connections allowed
    mincached=2,  # Minimum idle connections
    maxcached=5,  # Max idle connections
    maxshared=3,  # Max shared connections
    blocking=True,  # Block if no connections available
    maxusage=None,  # Max times a connection can be reused (None = unlimited)
    setsession=[],  # SQL commands to execute on new connections
    ping=1,  # Ping MySQL on checkout (0=never, 1=default, 2=when used, 4=always, 7=all)
    host='localhost',
    port=3306,
    user='root',
    password='',
    database='attendance_face',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False  # Manual transaction control
)

def get_db():
    """Get database connection from pool"""
    if 'db' not in g:
        g.db = pool.connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Return connection to pool at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()  # Returns connection to pool, doesn't actually close it

def login_required(func):
    @functools.wraps(func)
    def secure_function(*args, **kwargs):
        if "lid" not in session:
            return redirect(url_for('user'))
        return func(*args, **kwargs)
    return secure_function

def get_user_role(user_id):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT usertype FROM login WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        return result['usertype'] if result else None

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
    return redirect(url_for('user'))

@app.route('/login', methods=["GET", "POST"])
def user():
    if 'lid' in session:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get('textfield', '').strip()
        password = request.form.get('textfield2', '')
        
        if not username or not password:
            flash("Username and password required", "danger")
            return redirect(url_for('user'))
        
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, usertype FROM login WHERE username = %s AND password = %s", 
                (username, password)
            )
            result = cursor.fetchone()
            
        if result is None:
            flash("Invalid username or password", "danger")
            return redirect(url_for('user'))
        
        session['lid'] = result['id']
        role = result['usertype']
        
        if role == "admin":
            return redirect('/admin_home')
        elif role == "teacher":
            return redirect('/teacher_home')
        elif role == "student":
            return redirect('/student_home')
        
        return redirect(url_for('user'))

    response = make_response(render_template('login.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Expires'] = 0
    response.headers['Pragma'] = 'no-cache'
    return response

@app.route('/logout')
def logout():
    session.pop('lid', None)
    return redirect(url_for('user'))

@app.route('/student_signup', methods=['POST', 'GET'])
def student_signup():
    return render_template("student.html")

@app.route('/add_student', methods=['POST', 'GET'])
def add_student():
    db = get_db()
    try:
        # Get form data
        fname = request.form['text1']
        regno = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        dob = request.form['text6']
        dept = request.form['select']
        semester = request.form['select1']
        division = request.form['select3']
        guardian = request.form['guardian']
        guardian_phone = request.form['phone']

        # Handle file upload
        if 'files' not in request.files:
            flash("No file uploaded", "danger")
            return redirect(url_for('student_signup'))
        
        img = request.files['files']
        if img.filename == '':
            flash("No file selected", "danger")
            return redirect(url_for('student_signup'))

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
            flash("Password mismatch", "danger")
            return redirect(url_for('student_signup'))

        # Database operations with transaction
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO login VALUES (null, %s, %s, 'student')", 
                (uname, password)
            )
            lid = db.insert_id()
            
            cursor.execute(
                """INSERT INTO student VALUES 
                (null, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (lid, fname, regno, address, phone, email, dob, 
                 dept, semester, division, unique_filename, guardian, guardian_phone)
            )
        db.commit()
        flash("Successfully registered", "success")
        return redirect(url_for('user'))
            
    except Exception as e:
        db.rollback()
        print(f"Error in add_student: {str(e)}")
        flash("Registration failed", "danger")
        return redirect(url_for('student_signup'))

@app.route('/admin_home', methods=['POST', 'GET'])
@login_required
def admin_home():
    get_user_role(session['lid'])
    return render_template('admin/base.html')

@app.route('/view_staff', methods=['POST', 'GET'])
@login_required
def view_staff():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM teacher")
        res = cursor.fetchall()
    return render_template("admin/stafflist.html", val=res)

@app.route('/delete_staff', methods=['POST', 'GET'])
@login_required
def delete_staff():
    tlid = request.args.get('lid')
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM teacher WHERE lid=%s", (tlid,))
        db.commit()
        flash("Successfully deleted", "success")
        return redirect(url_for('view_staff'))
    except Exception as e:
        db.rollback()
        print(f"Error deleting staff: {str(e)}")
        flash("Error occurred", "danger")
        return redirect(url_for('view_staff'))

@app.route('/add_staff', methods=['POST', 'GET'])
@login_required
def add_staff():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT dept FROM department")
        dept = cursor.fetchall()
    return render_template("admin/staff_form.html", dept=dept)

@app.route('/staffreg', methods=['POST', 'GET'])
@login_required
def staffreg():
    db = get_db()
    try:
        fname = request.form['text1']
        code = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        qualification = request.form['text6']
        dept = request.form['select']
        
        img = request.files['files']
        filename = secure_filename(img.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        upload_path = os.path.join('./static/photos/staffphoto', unique_filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        img.save(upload_path)
        
        uname = request.form['uname']
        password = request.form['password']
        cnfpassword = request.form['cnfpassword']
        
        if password != cnfpassword:
            flash("Password mismatch", "danger")
            return redirect(url_for('add_staff'))
        
        with db.cursor() as cursor:
            cursor.execute("INSERT INTO login VALUES (null, %s, %s, 'teacher')", (uname, password))
            lid = db.insert_id()
            cursor.execute(
                "INSERT INTO teacher VALUES (null, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                (lid, fname, code, address, phone, email, qualification, dept, unique_filename)
            )
        db.commit()
        flash("Successfully added", "success")
        return redirect(url_for('view_staff'))
        
    except Exception as e:
        db.rollback()
        print(f"Error in staffreg: {str(e)}")
        flash("Error occurred", "danger")
        return redirect(url_for('add_staff'))

@app.route('/edit_staff', methods=['POST', 'GET'])
@login_required
def edit_staff():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """SELECT teacher.*, login.username 
            FROM teacher JOIN login ON teacher.lid = login.id 
            WHERE teacher.lid=%s""", 
            (request.args.get('lid'),)
        )
        res = cursor.fetchone()
        cursor.execute("SELECT dept FROM department")
        dept = cursor.fetchall()
    return render_template("admin/staff_form.html", val=res, dept=dept)

@app.route('/update_staff', methods=['POST', 'GET'])
@login_required
def update_staff():
    db = get_db()
    try:
        fname = request.form['text1']
        code = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        qualification = request.form['text6']
        dept = request.form['select']
        lid = request.form['lid']
        
        img = request.files.get('files')
        
        with db.cursor() as cursor:
            if img and img.filename:
                filename = secure_filename(img.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                upload_path = os.path.join('./static/photos/staffphoto', unique_filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                img.save(upload_path)
                
                cursor.execute(
                    """UPDATE teacher SET name=%s, teacher_code=%s, address=%s, 
                    phone=%s, email=%s, qualification=%s, department=%s, photo=%s 
                    WHERE lid=%s""", 
                    (fname, code, address, phone, email, qualification, dept, unique_filename, lid)
                )
            else:
                cursor.execute(
                    """UPDATE teacher SET name=%s, teacher_code=%s, address=%s, 
                    phone=%s, email=%s, qualification=%s, department=%s WHERE lid=%s""", 
                    (fname, code, address, phone, email, qualification, dept, lid)
                )
        db.commit()
        flash("Successfully updated", "success")
        return redirect(url_for('view_staff'))
        
    except Exception as e:
        db.rollback()
        print(f"Error updating staff: {str(e)}")
        flash("Error occurred", "danger")
        return redirect(url_for('edit_staff'))

@app.route('/view_student', methods=['POST', 'GET'])
@login_required
def view_student():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM student")
        res = cursor.fetchall()
    return render_template("admin/studentlist.html", val=res)

@app.route('/dept_search_student', methods=['POST', 'GET'])
@login_required
def dept_search_student():
    dept = request.form.get('selects')
    if not dept or dept == '-- Department --':
        flash("Please select a department to search for students.", "warning")
        return redirect(url_for('view_student'))
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM student WHERE department=%s", (dept,))
        res = cursor.fetchall()
    return render_template("admin/studentlist.html", val=res, dept=dept)

@app.route('/dept_search_staff', methods=['POST', 'GET'])
@login_required
def dept_search_staff():
    dept = request.form.get('select')
    if not dept or dept == '-- Department --':
        flash("Please select a department to search.", "warning")
        return redirect(url_for('view_staff'))
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM teacher WHERE department=%s", (dept,))
        res = cursor.fetchall()
    return render_template("admin/stafflist.html", val=res, dept=dept)

@app.route('/edit_student', methods=['POST', 'GET'])
@login_required
def edit_student():
    tlid = request.args.get('lid')
    session['slid'] = tlid
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM student WHERE lid=%s", (tlid,))
        res = cursor.fetchone()
    return render_template("admin/student_editform.html", i=res)

@app.route('/delete_student', methods=['POST', 'GET'])
@login_required
def delete_student():
    tlid = request.args.get('lid')
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM student WHERE lid=%s", (tlid,))
        db.commit()
        flash("Successfully deleted", "success")
        return redirect(url_for('view_student'))
    except Exception as e:
        db.rollback()
        print(f"Error deleting student: {str(e)}")
        flash("Error occurred", "danger")
        return redirect(url_for('view_student'))

@app.route('/view_subject', methods=['POST', 'GET'])
@login_required
def view_subject():
    return render_template("admin/subjectView.html")

@app.route('/view_subjects_dept_sem', methods=['POST', 'GET'])
@login_required
def view_subjects_dept_sem():
    dept = request.form.get('select')
    sem = request.form.get('select1')
    if not dept or dept == '--Department--' or not sem or sem == '--Semester--':
        flash("Please select both department and semester to view subjects.", "warning")
        return redirect(url_for('view_subject'))
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """SELECT `subject`.*, `teacher`.`name`, `teacher`.`teacher_code` 
            FROM `teacher` JOIN `subject` ON `subject`.`staff_lid`=`teacher`.`lid` 
            WHERE `subject`.`department`=%s AND `subject`.`semester`=%s""", 
            (dept, sem)
        )
        s = cursor.fetchall()
    return render_template("admin/subjectView.html", val=s, dept=dept, sem=sem)

@app.route('/delete_subject', methods=['POST', 'GET'])
@login_required
def delete_subject():
    sid = request.args.get('lid')
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM subject WHERE sid=%s", (sid,))
        db.commit()
        flash("Successfully deleted", "success")
        return redirect(url_for('view_subject'))
    except Exception as e:
        db.rollback()
        print(f"Error deleting subject: {str(e)}")
        flash("Error occurred", "danger")
        return redirect(url_for('view_subject'))

@app.route('/add_subject', methods=['POST', 'GET'])
@login_required
def add_subject():
    return render_template("admin/register_subject.html")

@app.route('/register_subject', methods=['POST', 'GET'])
@login_required
def register_subject():
    db = get_db()
    try:
        subject = request.form['text2']
        code = request.form['text1']
        dept = request.form['department']
        sem = request.form['Semester']
        staffid = request.form['Staff']
        
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO subject VALUES (null, %s, %s, %s, %s, %s)", 
                (subject, code, dept, sem, staffid)
            )
        db.commit()
        flash("Successfully registered", "success")
        return redirect(url_for('view_subject'))
    except Exception as e:
        db.rollback()
        print(f"Error registering subject: {str(e)}")
        flash("Error occurred", "danger")
        return redirect(url_for('add_subject'))

@app.route('/get_staff', methods=['POST'])
def get_staff():
    dept = request.form['dept']
    db = get_db()
    
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT `lid`, `name`, `teacher_code` FROM `teacher` WHERE `department`=%s", 
            (dept,)
        )
        staff = cursor.fetchall()

    staff_list = [{
        'id': s['lid'],
        'name': f"{s['name']} (CODE:{s['teacher_code']})"
    } for s in staff]
    
    return jsonify(staff_list), 200

@app.route('/add_timetable', methods=['POST', 'GET'])
@login_required
def add_timetable():
    # staffid=session['lid']
    # print("SELECT `department` FROM `teacher` WHERE `lid`='"+str(staffid)+"'")
    # cmd.execute("SELECT `department` FROM `teacher` WHERE `lid`='"+str(staffid)+"'")
    # s=cmd.fetchone()
    # dept=s[0]
    # session['dept']=dept
    return render_template("admin/addtimetable.html")

@app.route('/addtimetable', methods=['POST', 'GET'])
@login_required
def addtimetable():
    dept = request.form.get('select')
    sem = request.form.get('Semester')
    
    if not dept or dept == '--Department--' or not sem or sem == '--Select Semester--':
        flash("Please select both department and semester to create a timetable.", "warning")
        return redirect(url_for('add_timetable'))

    session['semess'] = sem
    session['deptt'] = dept
    
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM timetable WHERE `dept`=%s AND `sem`=%s", (dept, sem))
        existing = cursor.fetchone()
        
        if existing:
            flash("Timetable for this department and semester already exists.", "info")
            return redirect('/viewtimetable')
        
        # Get subjects for this department and semester
        cursor.execute(
            "SELECT * FROM `subject` WHERE `department`=%s AND `semester`=%s", 
            (dept, sem)
        )
        subjects = cursor.fetchall()
        
        if not subjects:
            flash("No subjects found for this department and semester. Cannot create timetable.", "danger")
            return redirect(url_for('add_timetable'))
        
        # Extract subject names
        subject_names = [s['subject'] for s in subjects]
        
        # Generate timetable
        hours_per_day = 7
        timetable = generate_timetable(subject_names, hours_per_day)
        
        # Flatten the timetable
        result_list = [timetable[key] for key in sorted(timetable.keys())]
        flattened = [item for sublist in result_list for item in sublist]
        
        # Insert timetable for each day
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for i, day in enumerate(days):
            start_idx = i * 7
            cursor.execute(
                """INSERT INTO timetable VALUES 
                (null, %s, %s, %s, %s, %s, %s, 'break', %s, %s, %s)""",
                (dept, sem, day, 
                 flattened[start_idx], flattened[start_idx+1], flattened[start_idx+2],
                 flattened[start_idx+4], flattened[start_idx+5], flattened[start_idx+6])
            )
    
    db.commit()
    flash("Timetable created successfully.", "success")
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

@app.route('/viewtimetable', methods=['POST', 'GET'])
@login_required
def viewtimetable():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """SELECT `day`, `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `h7`, `tid` 
            FROM `timetable` WHERE `dept`=%s AND `sem`=%s""", 
            (session.get('deptt'), session.get('semess'))
        )
        res = cursor.fetchall()
    return render_template("admin/timetableview.html", res=res)

@app.route('/view_timetables', methods=['POST', 'GET'])
@login_required
def view_timetables():
    dept = request.form.get('select')
    sem = request.form.get('Semester')

    if not dept or dept == '--Department--' or not sem or sem == '--Select Semester--':
        flash("Please select both department and semester to view the timetable.", "warning")
        return redirect(url_for('add_timetable')) # Redirect to add_timetable or view_timetable as appropriate

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """SELECT `day`, `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `h7`, `tid` 
            FROM `timetable` WHERE `dept`=%s AND `sem`=%s""", 
            (dept, sem)
        )
        res = cursor.fetchall()
    return render_template("admin/timetableview.html", res=res, dept=dept, sem=sem)

if __name__ == "__main__":
    app.run(debug=True)