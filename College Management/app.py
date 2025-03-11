from datetime import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_login import UserMixin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///college.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'



# User Model
class User(db.Model, UserMixin): 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) 

# Course Model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=False)  # Image filename

# Fee Payment Model
class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)

# Exam Schedule Model
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_date = db.Column(db.DateTime, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)  # ✅ Foreign Key

    course = db.relationship('Course', backref=db.backref('exams', lazy=True))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)

    student = db.relationship('User', backref='attendance', lazy=True)
    course = db.relationship('Course', backref='attendance', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')

# Admin Login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['user'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    courses = Course.query.all()
    
    exams = Exam.query.options(db.joinedload(Exam.course)).all()
    return render_template('admin_dashboard.html', courses=courses, exams=exams)


# Add Course
@app.route('/add_course', methods=['POST'])
def add_course():
    if 'user' not in session or session['user'] != 'admin':
        return redirect(url_for('admin_login'))
    name = request.form['name']
    image = request.files['image']
    image_path = f'static/uploads/{image.filename}'
    image.save(image_path)
    new_course = Course(name=name, image=image_path)
    db.session.add(new_course)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/add_fee', methods=['POST'])  
def add_fee():
    course_id = request.form['course_id']
    amount = request.form['amount']
    new_fee = Fee(course_id=course_id, amount=amount)
    db.session.add(new_fee)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/courses')
def courses():
    all_courses = Course.query.all()
    return render_template('courses.html', courses=all_courses)


@app.route('/book_course/<int:course_id>')
def book_course(course_id):
    course = Course.query.get(course_id)
    if course:
        flash(f'You have successfully booked {course.name}!', 'success')
    else:
        flash('Course not found!', 'danger')
    
    return redirect(url_for('student_dashboard'))  # Redirects to the correct page




# Add Exam Schedule
@app.route('/add_exam', methods=['POST'])
def add_exam():
    course_id = request.form['course_id']
    exam_date_str = request.form['exam_date']  # Get date as string from form

    # Convert string to datetime object
    exam_date = datetime.strptime(exam_date_str, '%Y-%m-%d')  # ✅ Correct format

    new_exam = Exam(course_id=course_id, exam_date=exam_date)  # ✅ Now it's a datetime object
    db.session.add(new_exam)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))


# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_user = User(username=username, password=password, role='student')
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        print("User:", user)  # Debugging: Check if user exists ✅

        if user and check_password_hash(user.password, password):  # ✅ Correct password check
            login_user(user)
            session['user_id'] = user.id  # ✅ Store user in session
            flash('Login successful!', 'success')

            if user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))

        else:
            flash('Invalid username or password', 'danger')  
            return redirect(url_for('login'))  # ❌ Redirecting back

    return render_template('login.html')



@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    student_id = request.form['student_id']
    course_id = request.form['course_id']
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_attendance = Attendance(student_id=student_id, course_id=course_id, date=date)
    db.session.add(new_attendance)
    db.session.commit()

    return redirect(url_for('student_dashboard'))

# Route to display student dashboard
@app.route('/student_dashboard')
def student_dashboard():
    student_id = session.get('user_id')  # Get logged-in student ID from session

    if not student_id:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    courses = Course.query.all()
    fees = Fee.query.all()
    exams = Exam.query.all()
    attendance_records = Attendance.query.filter_by(student_id=student_id).all()

    return render_template(
        'student_dashboard.html',
        courses=courses, 
        fees=fees, 
        exams=exams, 
        attendance_records=attendance_records
    )

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    if not os.path.exists('college.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
