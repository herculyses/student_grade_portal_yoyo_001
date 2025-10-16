from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired
import os, csv
from werkzeug.utils import secure_filename

# --- Flask Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Admin/Instructor/Student

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(50))  # changed from course
    grade = db.Column(db.String(10))
    remarks = db.Column(db.String(200))

# --- Forms ---
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('Instructor','Instructor'), ('Student','Student')], validators=[DataRequired()])
    submit = SubmitField('Create User')

class StudentForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    subject = StringField('Subject')
    grade = StringField('Grade')
    remarks = StringField('Remarks')
    submit = SubmitField('Save')

# --- Routes ---
@app.route('/', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data,password=form.password.data).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            flash(f'Logged in as {user.role}', 'success')
            if user.role == 'Admin':
                return redirect(url_for('dashboard_admin'))
            elif user.role == 'Instructor':
                return redirect(url_for('dashboard_instructor'))
            else:
                return redirect(url_for('dashboard_student'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Dashboards ---
@app.route('/dashboard/admin')
def dashboard_admin():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))
    return render_template('dashboard_admin.html')

@app.route('/dashboard/instructor')
def dashboard_instructor():
    if session.get('role') != 'Instructor':
        return redirect(url_for('login'))
    return render_template('dashboard_instructor.html')

@app.route('/dashboard/student')
def dashboard_student():
    if session.get('role') != 'Student':
        return redirect(url_for('login'))
    return render_template('dashboard_student.html')

# --- Admin creates users ---
@app.route('/dashboard/admin/create_user', methods=['GET','POST'])
def create_user():
    if session.get('role') != 'Admin':
        return redirect(url_for('login'))
    form = CreateUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists!', 'danger')
        else:
            db.session.add(User(username=form.username.data,password=form.password.data,role=form.role.data))
            db.session.commit()
            flash(f'{form.role.data} account created successfully!', 'success')
            return redirect(url_for('dashboard_admin'))
    return render_template('create_user.html', form=form)

# --- View students ---
@app.route('/dashboard/admin/students')
@app.route('/dashboard/instructor/students')
def view_students():
    if session.get('role') not in ['Admin','Instructor']:
        return redirect(url_for('login'))
    students = Student.query.all()
    return render_template('students.html', students=students)

# --- Add student ---
@app.route('/dashboard/admin/students/add', methods=['GET','POST'])
@app.route('/dashboard/instructor/students/add', methods=['GET','POST'])
def add_student():
    if session.get('role') not in ['Admin','Instructor']:
        return redirect(url_for('login'))
    form = StudentForm()
    if form.validate_on_submit():
        if Student.query.filter_by(student_id=form.student_id.data, subject=form.subject.data).first():
            flash('This student for the same subject already exists!', 'danger')
        else:
            new_student = Student(student_id=form.student_id.data, name=form.name.data,
                                  subject=form.subject.data, grade=form.grade.data, remarks=form.remarks.data)
            db.session.add(new_student)
            db.session.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('view_students'))
    return render_template('add_student.html', form=form)

# --- CSV Upload ---
@app.route('/dashboard/admin/students/upload', methods=['GET','POST'])
@app.route('/dashboard/instructor/students/upload', methods=['GET','POST'])
def upload_students():
    if session.get('role') not in ['Admin','Instructor']:
        return redirect(url_for('login'))
    if request.method=='POST':
        if 'file' not in request.files:
            flash('No file part','danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file','danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'],exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'],filename)
            file.save(filepath)
            with open(filepath,newline='',encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if not Student.query.filter_by(student_id=row['student_id'], subject=row['subject']).first():
                        db.session.add(Student(student_id=row['student_id'], name=row['name'],
                                               subject=row.get('subject',''),
                                               grade=row.get('grade',''),
                                               remarks=row.get('remarks','')))
            db.session.commit()
            flash('CSV uploaded successfully!','success')
            return redirect(url_for('view_students'))
        else:
            flash('Invalid file type. Only CSV allowed.','danger')
            return redirect(request.url)
    return render_template('upload_students.html')

# --- Initialize Database ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Default users
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(username='admin',password='admin123',role='Admin'))
        if not User.query.filter_by(username='instructor').first():
            db.session.add(User(username='instructor',password='instr123',role='Instructor'))
        if not User.query.filter_by(username='student').first():
            db.session.add(User(username='student',password='stud123',role='Student'))
        db.session.commit()
    app.run(debug=True)
