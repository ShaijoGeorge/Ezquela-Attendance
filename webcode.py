from flask import *
import pymysql
from flask_wtf import CSRFProtect
import secrets
import functools

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

if __name__ == "__main__":
    app.run(debug=True)