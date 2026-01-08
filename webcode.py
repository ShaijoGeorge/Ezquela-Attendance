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
    host=os.environ.get('DB_HOST', 'localhost'),
    port=3306,
    user=os.environ.get('DB_USER', 'root'),
    password=os.environ.get('DB_PASSWORD', ''),
    database=os.environ.get('DB_NAME', 'attendance_face'),
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
            return redirect('/staff_home')
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
            return redirect('/staff_home')
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
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT department_name FROM department")
        dept = cursor.fetchall()
    return render_template("student.html", dept=dept)

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
        dept_name = request.form['select']
        semester = request.form['select1']
        division = request.form['select3']
        gender = request.form.get('gender')
        guardian = request.form['guardian']
        guardian_phone = request.form['phone']
        uname = request.form['uname']
        password = request.form['password']
        cnfpassword = request.form['cnfpassword']

        # Validate required fields
        required_fields = {
            'Full Name': fname, 'Register Number': regno, 'Address': address,
            'Phone': phone, 'Email': email, 'Date of Birth': dob,
            'Department': dept_name, 'Semester': semester, 'Division': division,
            'Gender': gender, 'Guardian Name': guardian, 'Guardian Phone': guardian_phone,
            'Username': uname, 'Password': password
        }

        for field, value in required_fields.items():
            if not value or (isinstance(value, str) and not value.strip()):
                flash(f"{field} is required.", "danger")
                return redirect(url_for('student_signup'))
        
        if dept_name == "--Department--" or semester == "--Semester--" or division == "--Division--":
            flash("Please select valid department, semester, and division.", "danger")
            return redirect(url_for('student_signup'))

        # Handle file upload
        if 'files' not in request.files or request.files['files'].filename == '':
            flash("Photo is required.", "danger")
            return redirect(url_for('student_signup'))
        
        img = request.files['files']
        
        # Generate unique filename
        filename = secure_filename(img.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        upload_path = os.path.join('./static/photos/studentphoto', unique_filename)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        img.save(upload_path)
        
        if password != cnfpassword:
            flash("Password mismatch", "danger")
            return redirect(url_for('student_signup'))

        # Database operations with transaction
        with db.cursor() as cursor:
            
            # Get department_id from department_name
            cursor.execute(
                "SELECT department_id FROM department WHERE department_name = %s", 
                (dept_name,)
            )
            dept_result = cursor.fetchone()
            if not dept_result:
                flash("Invalid department selected", "danger")
                return redirect(url_for('student_signup'))
            
            dept_id = dept_result['department_id']

            # Insert student data
            cursor.execute(
                "INSERT INTO login VALUES (null, %s, %s, 'student')", 
                (uname, password)
            )
            lid = db.insert_id()
            
            # Insert with department_id instead of department
            cursor.execute(
                """INSERT INTO student (stid, lid, name, regno, address, phone, email, 
                dob, semester, division, photo, gname, gnumber, gender, department_id) VALUES 
                (null, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (lid, fname, regno, address, phone, email, dob, 
                 semester, division, unique_filename, guardian, guardian_phone, gender, dept_id)
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

@app.route('/admin/departments', methods=['GET'])
@login_required
def manage_departments():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT d.*, c.course_name 
            FROM department d 
            LEFT JOIN courses c ON d.course_id = c.course_id 
            ORDER BY d.department_name
        """)
        departments = cursor.fetchall()
        cursor.execute("SELECT * FROM courses ORDER BY course_name")
        courses = cursor.fetchall()
    return render_template('admin/departments.html', departments=departments, courses=courses)

@app.route('/admin/add_department', methods=['POST'])
@login_required
def add_department():
    department_name = request.form.get('department_name', '').strip()
    course_id = request.form.get('course_id')

    if not department_name or not course_id:
        flash("All fields are required.", "danger")
        return redirect(url_for('manage_departments'))

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO department (department_name, course_id) VALUES (%s, %s)",
                (department_name, course_id)
            )
        db.commit()
        flash("Department added successfully.", "success")
    except pymysql.IntegrityError:
        db.rollback()
        flash("Department with this name already exists.", "danger")
    except Exception as e:
        db.rollback()
        print(f"Error adding department: {str(e)}")
        flash("An error occurred while adding the department.", "danger")
    
    return redirect(url_for('manage_departments'))

@app.route('/admin/update_department/<int:department_id>', methods=['POST'])
@login_required
def update_department(department_id):
    department_name = request.form.get('department_name', '').strip()
    course_id = request.form.get('course_id')

    if not department_name or not course_id:
        flash("All fields are required.", "danger")
        return redirect(url_for('manage_departments'))

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE department SET department_name = %s, course_id = %s WHERE department_id = %s",
                (department_name, course_id, department_id)
            )
        db.commit()
        flash("Department updated successfully.", "success")
    except pymysql.IntegrityError:
        db.rollback()
        flash("Another department with this name already exists.", "danger")
    except Exception as e:
        db.rollback()
        print(f"Error updating department: {str(e)}")
        flash("An error occurred while updating the department.", "danger")
        
    return redirect(url_for('manage_departments'))

@app.route('/admin/delete_department/<int:department_id>', methods=['GET'])
@login_required
def delete_department(department_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM department WHERE department_id = %s", (department_id,))
        db.commit()
        flash("Department deleted successfully.", "success")
    except Exception as e:
        db.rollback()
        print(f"Error deleting department: {str(e)}")
        flash("An error occurred while deleting the department.", "danger")
    
    return redirect(url_for('manage_departments'))

@app.route('/admin/departments_search', methods=['POST', 'GET'])
@login_required
def departments_search():
    course = request.form.get('select_course')
    db = get_db()
    with db.cursor() as cursor:
        if course and course != '-- Course --':
            cursor.execute("""
                SELECT d.*, c.course_name 
                FROM department d 
                LEFT JOIN courses c ON d.course_id = c.course_id 
                WHERE c.course_name = %s
                ORDER BY d.department_name
            """, (course,))
        else:
            cursor.execute("""
                SELECT d.*, c.course_name 
                FROM department d 
                LEFT JOIN courses c ON d.course_id = c.course_id 
                ORDER BY d.department_name
            """)
        
        departments = cursor.fetchall()
        cursor.execute("SELECT * FROM courses ORDER BY course_name")
        courses = cursor.fetchall()
    return render_template('admin/departments.html', departments=departments, courses=courses, course=course)

@app.route('/admin/courses', methods=['GET'])
@login_required
def manage_courses():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM courses ORDER BY course_name")
        courses = cursor.fetchall()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/add_course', methods=['POST'])
@login_required
def add_course():
    course_name = request.form.get('course_name', '').strip()
    course_code = request.form.get('course_code', '').strip()

    if not course_name or not course_code:
        flash("All fields are required.", "danger")
        return redirect(url_for('manage_courses'))

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO courses (course_name, course_code) VALUES (%s, %s)",
                (course_name, course_code)
            )
        db.commit()
        flash("Course added successfully.", "success")
    except pymysql.IntegrityError:
        db.rollback()
        flash("A course with this name or code already exists.", "danger")
    except Exception as e:
        db.rollback()
        print(f"Error adding course: {str(e)}")
        flash("An error occurred while adding the course.", "danger")
    
    return redirect(url_for('manage_courses'))

@app.route('/admin/update_course/<int:course_id>', methods=['POST'])
@login_required
def update_course(course_id):
    course_name = request.form.get('course_name', '').strip()
    course_code = request.form.get('course_code', '').strip()

    if not course_name or not course_code:
        flash("All fields are required.", "danger")
        return redirect(url_for('manage_courses'))

    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE courses SET course_name = %s, course_code = %s WHERE course_id = %s",
                (course_name, course_code, course_id)
            )
        db.commit()
        flash("Course updated successfully.", "success")
    except pymysql.IntegrityError:
        db.rollback()
        flash("Another course with this name or code already exists.", "danger")
    except Exception as e:
        db.rollback()
        print(f"Error updating course: {str(e)}")
        flash("An error occurred while updating the course.", "danger")
        
    return redirect(url_for('manage_courses'))

@app.route('/admin/delete_course/<int:course_id>', methods=['GET'])
@login_required
def delete_course(course_id):
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        db.commit()
        flash("Course deleted successfully.", "success")
    except Exception as e:
        db.rollback()
        print(f"Error deleting course: {str(e)}")
        flash("An error occurred while deleting the course.", "danger")
    
    return redirect(url_for('manage_courses'))

@app.route('/view_staff', methods=['POST', 'GET'])
@login_required
def view_staff():
    db = get_db()
    with db.cursor() as cursor:
        # Join with department table to get department_name
        cursor.execute("""
            SELECT t.*, d.department_name as department 
            FROM teacher t 
            LEFT JOIN department d ON t.department_id = d.department_id
        """)
        res = cursor.fetchall()
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()
    return render_template("admin/stafflist.html", val=res, dept_list=dept_list, course_list=course_list)

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
        cursor.execute("SELECT department_name FROM department")
        dept = cursor.fetchall()
    return render_template("admin/staff_form.html", dept=dept)

@app.route('/staffreg', methods=['POST', 'GET'])
@login_required
def staffreg():
    db = get_db()
    try:
        fname = request.form.get('text1')
        code = request.form.get('text2')
        address = request.form.get('text3')
        phone = request.form.get('text4')
        email = request.form.get('text5')
        qualification = request.form.get('text6')
        dept_name = request.form.get('select')
        gender = request.form.get('gender')
        uname = request.form.get('uname')
        password = request.form.get('password')
        cnfpassword = request.form.get('cnfpassword')

        if not all([fname, code, address, phone, email, qualification, dept_name, gender, uname, password, cnfpassword]):
            flash("All fields are required.", "danger")
            return redirect(url_for('add_staff'))
        
        if 'files' not in request.files or request.files['files'].filename == '':
            flash("Photo is required.", "danger")
            return redirect(url_for('add_staff'))

        img = request.files['files']
        filename = secure_filename(img.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        upload_path = os.path.join('./static/photos/staffphoto', unique_filename)
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        img.save(upload_path)
        
        if password != cnfpassword:
            flash("Password mismatch", "danger")
            return redirect(url_for('add_staff'))
        
        with db.cursor() as cursor:
            # Get department_id from department_name
            cursor.execute(
                "SELECT department_id FROM department WHERE department_name = %s", 
                (dept_name,)
            )
            dept_result = cursor.fetchone()
            if not dept_result:
                flash("Invalid department selected", "danger")
                return redirect(url_for('add_staff'))
            
            dept_id = dept_result['department_id']
            
            cursor.execute("INSERT INTO login VALUES (null, %s, %s, 'teacher')", (uname, password))
            lid = db.insert_id()
            
            cursor.execute(
                """INSERT INTO teacher (tid, lid, name, teacher_code, address, phone, 
                email, qualification, photo, gender, department_id) VALUES 
                (null, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
                (lid, fname, code, address, phone, email, qualification, unique_filename, gender, dept_id)
            )
        db.commit()
        flash("Successfully added", "success")
        return redirect(url_for('view_staff'))
        
    except Exception as e:
        db.rollback()
        print(f"Error in staffreg: {str(e)}")
        flash(f"Error occurred: {str(e)}", "danger")
        return redirect(url_for('add_staff'))

@app.route('/view_staff_details', methods=['GET'])
@login_required
def view_staff_details():
    lid = request.args.get('lid')
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, d.department_name as department
            FROM teacher t
            LEFT JOIN department d ON t.department_id = d.department_id
            WHERE t.lid = %s
        """, (lid,))
        staff = cursor.fetchone()
    
    if staff:
        return render_template("admin/staff_view.html", staff=staff)
    else:
        flash("Staff member not found.", "danger")
        return redirect(url_for('view_staff'))
    
@app.route('/edit_staff', methods=['GET'])
@login_required
def edit_staff():
    db = get_db()
    with db.cursor() as cursor:
        # Join to get department_name
        cursor.execute(
            """SELECT t.*, l.username, d.department_name as department 
            FROM teacher t 
            JOIN login l ON t.lid = l.id 
            LEFT JOIN department d ON t.department_id = d.department_id 
            WHERE t.lid=%s""", 
            (request.args.get('lid'),)
        )
        res = cursor.fetchone()
        cursor.execute("SELECT department_name FROM department")
        dept = cursor.fetchall()
    return render_template("admin/staff_form.html", val=res, dept=dept)

@app.route('/update_staff', methods=['POST', 'GET'])
@login_required
def update_staff():
    db = get_db()
    # Get lid first, before any potential exceptions
    lid = request.form.get('lid')
    
    try:
        fname = request.form['text1']
        code = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        qualification = request.form['text6']
        dept_name = request.form['select']  # This is department_name
        gender = request.form.get('gender')  # Use .get() to avoid KeyError
        
        # Validate required fields
        if not gender:
            flash("Gender field is required", "danger")
            return redirect(url_for('edit_staff', lid=lid))
        
        img = request.files.get('files')
        
        with db.cursor() as cursor:
            # Get department_id from department_name
            cursor.execute(
                "SELECT department_id FROM department WHERE department_name = %s", 
                (dept_name,)
            )
            dept_result = cursor.fetchone()
            if not dept_result:
                flash("Invalid department selected", "danger")
                return redirect(url_for('edit_staff', lid=lid))
            
            dept_id = dept_result['department_id']
            
            if img and img.filename:
                filename = secure_filename(img.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                upload_path = os.path.join('./static/photos/staffphoto', unique_filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                img.save(upload_path)
                
                cursor.execute(
                    """UPDATE teacher SET name=%s, teacher_code=%s, address=%s, 
                    phone=%s, email=%s, qualification=%s, department_id=%s, photo=%s, gender=%s 
                    WHERE lid=%s""", 
                    (fname, code, address, phone, email, qualification, dept_id, unique_filename, gender, lid)
                )
            else:
                cursor.execute(
                    """UPDATE teacher SET name=%s, teacher_code=%s, address=%s, 
                    phone=%s, email=%s, qualification=%s, department_id=%s, gender=%s WHERE lid=%s""", 
                    (fname, code, address, phone, email, qualification, dept_id, gender, lid)
                )
        db.commit()
        flash("Successfully updated", "success")
        return redirect(url_for('view_staff'))
        
    except Exception as e:
        db.rollback()
        print(f"Error updating staff: {str(e)}")
        flash(f"Error occurred: {str(e)}", "danger")
        # lid is now safely defined at the start of the function
        return redirect(url_for('edit_staff', lid=lid))

@app.route('/view_student_details', methods=['GET'])
@login_required
def view_student_details():
    lid = request.args.get('lid')
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT s.*, d.department_name as department, c.course_name as course
            FROM student s
            LEFT JOIN department d ON s.department_id = d.department_id
            LEFT JOIN courses c ON d.course_id = c.course_id
            WHERE s.lid = %s
        """, (lid,))
        student = cursor.fetchone()
    
    if student:
        return render_template("admin/student_view.html", student=student)
    else:
        flash("Student not found.", "danger")
        return redirect(url_for('view_student'))

@app.route('/view_student', methods=['POST', 'GET'])
@login_required
def view_student():
    db = get_db()
    with db.cursor() as cursor:
        # Join with department table to get department_name
        cursor.execute("""
            SELECT s.*, d.department_name as department 
            FROM student s 
            LEFT JOIN department d ON s.department_id = d.department_id
        """)
        res = cursor.fetchall()
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()
    return render_template("admin/studentlist.html", val=res, dept_list=dept_list, course_list=course_list)

@app.route('/dept_search_student', methods=['POST', 'GET'])
@login_required
def dept_search_student():
    dept = request.form.get('selects')
    sem = request.form.get('select1')
    course = request.form.get('select_course')
    
    db = get_db()
    with db.cursor() as cursor:
        
        query = """
            SELECT s.*, d.department_name as department 
            FROM student s 
            LEFT JOIN department d ON s.department_id = d.department_id
            LEFT JOIN courses c ON d.course_id = c.course_id
            WHERE 1=1
        """
        params = []

        if dept and dept != '-- Department --':
            query += " AND d.department_name = %s"
            params.append(dept)
        
        if sem and sem != '-- Semester --':
            query += " AND s.semester = %s"
            params.append(sem)

        if course and course != '-- Course --':
            query += " AND c.course_name = %s"
            params.append(course)

        cursor.execute(query, tuple(params))
        res = cursor.fetchall()
        
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()
    
    return render_template("admin/studentlist.html", val=res, dept_list=dept_list, course_list=course_list, dept=dept, sem=sem, course=course)

@app.route('/dept_search_staff', methods=['POST', 'GET'])
@login_required
def dept_search_staff():
    dept = request.form.get('select')
    course = request.form.get('select_course')

    db = get_db()
    with db.cursor() as cursor:
        query = """
            SELECT t.*, d.department_name as department 
            FROM teacher t
            LEFT JOIN department d ON t.department_id = d.department_id
            LEFT JOIN courses c ON d.course_id = c.course_id
            WHERE 1=1
        """
        params = []

        if dept and dept != '-- Department --':
            query += " AND d.department_name = %s"
            params.append(dept)

        if course and course != '-- Course --':
            query += " AND c.course_name = %s"
            params.append(course)

        cursor.execute(query, tuple(params))
        res = cursor.fetchall()

        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()

    return render_template("admin/stafflist.html", val=res, dept_list=dept_list, course_list=course_list, dept=dept, course=course)

@app.route('/edit_student', methods=['POST', 'GET'])
@login_required
def edit_student():
    tlid = request.args.get('lid')
    session['slid'] = tlid
    db = get_db()
    with db.cursor() as cursor:
        # Join with department table to get department_name
        cursor.execute("""
            SELECT s.*, d.department_name as department 
            FROM student s 
            LEFT JOIN department d ON s.department_id = d.department_id 
            WHERE s.lid = %s
        """, (tlid,))
        res = cursor.fetchone()
        cursor.execute("SELECT department_name FROM department")
        dept = cursor.fetchall()
    return render_template("admin/student_editform.html", i=res, dept=dept)


@app.route('/update_student', methods=['POST'])
@login_required
def update_student():
    db = get_db()
    lid = request.form.get('lid')
    try:
        fname = request.form['text1']
        regno = request.form['text2']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        dob = request.form['text6']
        dept_name = request.form['select']
        semester = request.form['select1']
        division = request.form['select3']
        gender = request.form.get('gender')
        guardian = request.form['guardian']
        guardian_phone = request.form['phone']

        # Validate required fields
        required_fields = {
            'Full Name': fname, 'Register Number': regno, 'Address': address,
            'Phone': phone, 'Email': email, 'Date of Birth': dob,
            'Department': dept_name, 'Semester': semester, 'Division': division,
            'Gender': gender, 'Guardian Name': guardian, 'Guardian Phone': guardian_phone
        }

        for field, value in required_fields.items():
            if not value or (isinstance(value, str) and not value.strip()):
                flash(f"{field} is required.", "danger")
                return redirect(url_for('edit_student', lid=lid))
        
        if dept_name == "--Department--" or semester == "--Semester--" or division == "--Division--":
            flash("Please select valid department, semester, and division.", "danger")
            return redirect(url_for('edit_student', lid=lid))

        img = request.files.get('files')
        
        with db.cursor() as cursor:
            # Get department_id from department_name
            cursor.execute(
                "SELECT department_id FROM department WHERE department_name = %s", 
                (dept_name,)
            )
            dept_result = cursor.fetchone()
            if not dept_result:
                flash("Invalid department selected", "danger")
                return redirect(url_for('edit_student', lid=lid))
            
            dept_id = dept_result['department_id']
            
            if img and img.filename:
                filename = secure_filename(img.filename)
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                upload_path = os.path.join('./static/photos/studentphoto', unique_filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                img.save(upload_path)
                
                cursor.execute(
                    """UPDATE student SET name=%s, regno=%s, address=%s, 
                    phone=%s, email=%s, dob=%s, department_id=%s, semester=%s, 
                    division=%s, photo=%s, gname=%s, gnumber=%s, gender=%s
                    WHERE lid=%s""", 
                    (fname, regno, address, phone, email, dob, dept_id, semester, 
                     division, unique_filename, guardian, guardian_phone, gender, lid)
                )
            else:
                cursor.execute(
                    """UPDATE student SET name=%s, regno=%s, address=%s, 
                    phone=%s, email=%s, dob=%s, department_id=%s, semester=%s, 
                    division=%s, gname=%s, gnumber=%s, gender=%s
                    WHERE lid=%s""", 
                    (fname, regno, address, phone, email, dob, dept_id, semester, 
                     division, guardian, guardian_phone, gender, lid)
                )
        db.commit()
        flash("Successfully updated", "success")
        return redirect(url_for('view_student'))
        
    except Exception as e:
        db.rollback()
        print(f"Error updating student: {str(e)}")
        flash(f"Error occurred: {str(e)}", "danger")
        return redirect(url_for('edit_student', lid=lid))

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
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()
    return render_template("admin/subjectView.html", dept_list=dept_list, course_list=course_list)

@app.route('/view_subjects_dept_sem', methods=['POST', 'GET'])
@login_required
def view_subjects_dept_sem():
    dept = request.form.get('select')
    sem = request.form.get('select1')
    course = request.form.get('select_course')

    db = get_db()
    with db.cursor() as cursor:
        query = """
            SELECT s.*, t.name, t.teacher_code, d.department_name as department 
            FROM subject s 
            JOIN teacher t ON s.staff_lid = t.lid 
            LEFT JOIN department d ON s.department_id = d.department_id
            LEFT JOIN courses c ON d.course_id = c.course_id
            WHERE 1=1
        """
        params = []

        if dept and dept != '--Department--':
            query += " AND d.department_name = %s"
            params.append(dept)
        
        if sem and sem != '--Semester--':
            query += " AND s.semester = %s"
            params.append(sem)

        if course and course != '--Course--':
            query += " AND c.course_name = %s"
            params.append(course)

        cursor.execute(query, tuple(params))
        s = cursor.fetchall()

        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()

    return render_template("admin/subjectView.html", val=s, dept_list=dept_list, course_list=course_list, dept=dept, sem=sem, course=course)

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
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
    return render_template("admin/register_subject.html", dept_list=dept_list)

@app.route('/register_subject', methods=['POST', 'GET'])
@login_required
def register_subject():
    db = get_db()
    try:
        subject = request.form['text2']
        code = request.form['text1']
        dept_name = request.form['department']
        sem = request.form['Semester']
        staffid = request.form['Staff']
        
        with db.cursor() as cursor:
            # Get department_id from department_name
            cursor.execute(
                "SELECT department_id FROM department WHERE department_name = %s", 
                (dept_name,)
            )
            dept_result = cursor.fetchone()
            if not dept_result:
                flash("Invalid department selected", "danger")
                return redirect(url_for('add_subject'))
            
            dept_id = dept_result['department_id']
            
            # Insert with department_id
            cursor.execute(
                """INSERT INTO subject (sid, subject, code, semester, staff_lid, department_id) 
                VALUES (null, %s, %s, %s, %s, %s)""", 
                (subject, code, sem, staffid, dept_id)
            )
        db.commit()
        flash("Successfully registered", "success")
        return redirect(url_for('view_subject'))
    except Exception as e:
        db.rollback()
        print(f"Error registering subject: {str(e)}")
        flash(f"Error occurred: {str(e)}", "danger")
        return redirect(url_for('add_subject'))

@app.route('/get_staff', methods=['POST'])
def get_staff():
    dept_name = request.form['dept']
    db = get_db()
    
    with db.cursor() as cursor:
        # Join with department table to filter by department_name
        cursor.execute(
            """SELECT t.lid, t.name, t.teacher_code 
            FROM teacher t 
            LEFT JOIN department d ON t.department_id = d.department_id 
            WHERE d.department_name = %s""", 
            (dept_name,)
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
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
    return render_template("admin/addtimetable.html", dept_list=dept_list)

@app.route('/addtimetable', methods=['POST', 'GET'])
@login_required
def addtimetable():
    dept_name = request.form.get('select')
    sem = request.form.get('Semester')
    
    if not dept_name or dept_name == '-- Select Department --' or not sem or sem == '-- Select Semester --':
        flash("Please select both department and semester to create a timetable.", "warning")
        return redirect(url_for('add_timetable'))

    session['semess'] = sem
    session['deptt'] = dept_name
    
    db = get_db()
    with db.cursor() as cursor:
        # Get department_id
        cursor.execute(
            "SELECT department_id FROM department WHERE department_name = %s", 
            (dept_name,)
        )
        dept_result = cursor.fetchone()
        if not dept_result:
            flash("Invalid department selected", "danger")
            return redirect(url_for('add_timetable'))
        
        dept_id = dept_result['department_id']
        
        # Check if timetable exists using department_id
        cursor.execute(
            "SELECT * FROM timetable WHERE department_id = %s AND sem = %s", 
            (dept_id, sem)
        )
        existing = cursor.fetchone()
        
        if existing:
            flash("Timetable for this department and semester already exists.", "info")
            return redirect('/viewtimetable')
        
        # Get subjects for this department and semester using department_id
        cursor.execute(
            "SELECT * FROM subject WHERE department_id = %s AND semester = %s", 
            (dept_id, sem)
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
        
        # Insert timetable for each day with department_id
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for i, day in enumerate(days):
            start_idx = i * 7
            cursor.execute(
                """INSERT INTO timetable (tid, sem, day, h1, h2, h3, h4, h5, h6, h7, department_id) 
                VALUES (null, %s, %s, %s, %s, %s, 'break', %s, %s, %s, %s)""",
                (sem, day, 
                 flattened[start_idx], flattened[start_idx+1], flattened[start_idx+2],
                 flattened[start_idx+4], flattened[start_idx+5], flattened[start_idx+6], dept_id)
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
        # Get department_id from session department name
        dept_name = session.get('deptt')
        cursor.execute(
            "SELECT department_id FROM department WHERE department_name = %s", 
            (dept_name,)
        )
        dept_result = cursor.fetchone()
        
        if dept_result:
            dept_id = dept_result['department_id']
            cursor.execute(
                """SELECT day, h1, h2, h3, h4, h5, h6, h7, tid 
                FROM timetable WHERE department_id = %s AND sem = %s""", 
                (dept_id, session.get('semess'))
            )
            res = cursor.fetchall()
        else:
            res = []
            
        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()
    return render_template("admin/timetable.html", res=res, dept_list=dept_list, course_list=course_list)

@app.route('/view_timetables', methods=['POST', 'GET'])
@login_required
def view_timetables():
    dept_name = request.form.get('select')
    sem = request.form.get('Semester')
    course = request.form.get('select_course')

    db = get_db()
    with db.cursor() as cursor:
        query = """
            SELECT tt.day, tt.h1, tt.h2, tt.h3, tt.h4, tt.h5, tt.h6, tt.h7, tt.tid 
            FROM timetable tt
            LEFT JOIN department d ON tt.department_id = d.department_id
            LEFT JOIN courses c ON d.course_id = c.course_id
            WHERE 1=1
        """
        params = []

        if dept_name and dept_name != '--Department--':
            query += " AND d.department_name = %s"
            params.append(dept_name)
        
        if sem and sem != '--Select Semester--':
            query += " AND tt.sem = %s"
            params.append(sem)

        if course and course != '--Course--':
            query += " AND c.course_name = %s"
            params.append(course)

        cursor.execute(query, tuple(params))
        res = cursor.fetchall()

        cursor.execute("SELECT department_name FROM department")
        dept_list = cursor.fetchall()
        cursor.execute("SELECT course_name FROM courses")
        course_list = cursor.fetchall()

    return render_template("admin/timetableview.html", res=res, dept_list=dept_list, course_list=course_list, dept=dept_name, sem=sem, course=course)

# Staff Home Dashboard
@app.route('/staff_home')
@login_required
def staff_home():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, d.department_name
            FROM teacher t
            LEFT JOIN department d ON t.department_id = d.department_id
            WHERE t.lid = %s
        """, (session['lid'],))
        teacher = cursor.fetchone()

        if not teacher:
            flash("Staff profile not found.", "danger")
            return redirect(url_for('user'))

        # Keep only what is needed in session (already used elsewhere)
        session['dept_id'] = teacher['department_id']

        # Attendance shortage
        cursor.execute("""
            SELECT s.name, s.lid,
                   COUNT(CASE WHEN a.attendance = 0 THEN 1 END) AS absent_days
            FROM student s
            LEFT JOIN attendence a ON s.lid = a.studentlid
            WHERE s.department_id = %s
            GROUP BY s.lid, s.name
            HAVING absent_days >= 2
        """, (teacher['department_id'],))
        shortage_list = cursor.fetchall()

    return render_template("staff/staffindex.html", teacher=teacher, shortage_count=len(shortage_list)
)

# Staff Profile View
@app.route('/staff_profile')
@login_required
def staff_profile():
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, d.department_name 
            FROM teacher t 
            LEFT JOIN department d ON t.department_id = d.department_id 
            WHERE t.lid = %s
        """, (session['lid'],))
        profile = cursor.fetchone()
    
    # Pass 'teacher' for base.html AND 'i' for the profile form
    return render_template("staff/staff_profile.html", i=profile, teacher=profile)

# Update Staff Profile
@app.route('/update_staff_profile', methods=['POST'])
@login_required
def update_staff_profile():
    try:
        db = get_db()
        name = request.form['text1']
        address = request.form['text3']
        phone = request.form['text4']
        email = request.form['text5']
        
        with db.cursor() as cursor:
            cursor.execute("""
                UPDATE teacher 
                SET name=%s, address=%s, phone=%s, email=%s 
                WHERE lid=%s
            """, (name, address, phone, email, session['lid']))
        db.commit()
        flash("Profile updated successfully", "success")
        return redirect(url_for('staff_profile'))
    except Exception as e:
        flash("Update failed", "danger")
        return redirect(url_for('staff_profile'))
    
# ATTENDANCE MANAGEMENT MODULE
@app.route('/staff_view_attendance', methods=['POST', 'GET'])
@login_required
def staff_view_attendance():
    db = get_db()
    data = []
    
    # Fetch full teacher info for the sidebar
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM teacher WHERE lid=%s", (session['lid'],))
        teacher = cursor.fetchone()
    
    if request.method == 'POST':
        date = request.form['date']
        hour = request.form['hour']
        
        with db.cursor() as cursor:
            # Use the fetched teacher's department_id
            if teacher:
                cursor.execute("""
                    SELECT s.name, s.regno, a.attendance, a.status 
                    FROM attendence a
                    JOIN student s ON a.studentlid = s.lid
                    WHERE a.date = %s AND a.hour = %s AND a.department_id = %s
                """, (date, hour, teacher['department_id']))
                data = cursor.fetchall()
                
    return render_template("staff/attendance.html", val=data, teacher=teacher)

@app.route('/take_attendance', methods=['POST', 'GET'])
@login_required
def take_attendance():
    db = get_db()
    with db.cursor() as cursor:
        # Fetch full teacher info (was only department_id before)
        cursor.execute("SELECT * FROM teacher WHERE lid=%s", (session['lid'],))
        teacher = cursor.fetchone()
        
        if not teacher:
            flash("Error: Staff department not found", "danger")
            return redirect(url_for('staff_home'))

        dept_id = teacher['department_id']

        # Get Subjects
        cursor.execute("SELECT * FROM subject WHERE department_id = %s", (dept_id,))
        subjects = cursor.fetchall()

    if request.method == 'POST':
        session['att_sub'] = request.form['subject']
        session['att_hour'] = request.form['hour']
        session['att_sem'] = request.form['semester']
        session['att_div'] = request.form.get('division', 'A')
        
        # Pass teacher here too
        return render_template("staff/stopclass.html", teacher=teacher) 

    return render_template("staff/takeattedance.html", subjects=subjects, teacher=teacher)

@app.route('/mark_attendance_face', methods=['POST'])
@login_required
def mark_attendance_face():
    # This route is called by JavaScript in stopclass.html
    try:
        import base64
        
        # 1. Get the image from the JSON request
        data = request.json
        image_data = data['image'].split(',')[1] # Remove "data:image/jpeg;base64," header
        
        # 2. Save temporary file
        filename = f"temp_{session['lid']}.jpg"
        filepath = os.path.join("static", "test", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "wb") as fh:
            fh.write(base64.b64decode(image_data))
            
        # 3. Predict Face
        from facemaster import predict_face
        student_lid, confidence = predict_face(filepath)
        
        response = {"status": "failed", "message": "Face not recognized"}
        
        if student_lid:
            db = get_db()
            with db.cursor() as cursor:
                # Get Staff Department again
                cursor.execute("SELECT department_id FROM teacher WHERE lid=%s", (session['lid'],))
                dept_id = cursor.fetchone()['department_id']
                
                # Check if already marked for this hour
                cursor.execute("""
                    SELECT aid FROM attendence 
                    WHERE studentlid=%s AND date=CURDATE() AND hour=%s
                """, (student_lid, session['att_hour']))
                
                if not cursor.fetchone():
                    # Insert Present Record
                    cursor.execute("""
                        INSERT INTO attendence 
                        (studentlid, date, attendance, hour, sem, division, department_id, subid, status)
                        VALUES (%s, CURDATE(), 1, %s, %s, %s, %s, %s, 'present')
                    """, (student_lid, session['att_hour'], session['att_sem'], 
                          session['att_div'], dept_id, session['att_sub']))
                    db.commit()
                    response = {
                        "status": "success", 
                        "message": f"Marked Present: Student ID {student_lid}",
                        "student_id": student_lid
                    }
                else:
                    response = {"status": "info", "message": "Already marked present"}
                    
        return jsonify(response)
        
    except Exception as e:
        print(e)
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
