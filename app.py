from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os, csv

# --- Flask Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

uri = os.getenv("DATABASE_URL", "sqlite:///app.db")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = uri
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
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Admin/Instructor/Student

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(50))
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

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired()])
    submit = SubmitField('Change Password')

# --- Login Required Decorator ---
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in first.", "danger")
                return redirect(url_for('login'))
            if role and session.get('role') not in (role if isinstance(role, list) else [role]):
                flash("Access denied.", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes ---

@app.route('/', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Logged in successfully as {user.username}', 'success')
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

@app.route('/change_password', methods=['GET', 'POST'])
@login_required()
def change_password():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not check_password_hash(user.password, current_password):
            flash("❌ Current password is incorrect.", "danger")
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash("⚠️ New passwords do not match.", "warning")
            return redirect(url_for('change_password'))

        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash("✅ Password changed successfully!", "success")

        # Redirect based on role
        if user.role == 'Admin':
            return redirect(url_for('dashboard_admin'))
        elif user.role == 'Instructor':
            return redirect(url_for('dashboard_instructor'))
        else:
            return redirect(url_for('dashboard_student'))

    return render_template('change_password.html')



# --- Dashboards ---
@app.route('/dashboard/admin')
@login_required(role='Admin')
def dashboard_admin():
    students = Student.query.all()
    return render_template('dashboard_admin.html', students=students)

@app.route('/dashboard/instructor')
@login_required(role='Instructor')
def dashboard_instructor():
    return render_template('dashboard_instructor.html')

@app.route('/dashboard/student')
@login_required(role='Student')
def dashboard_student():
    student_username = session.get('username')
    
    # Fetch all records for this student
    students = Student.query.filter_by(student_id=student_username).all()
    
    # Get the student's actual name from the first record
    student_name = students[0].name if students else student_username

    return render_template('dashboard_student.html', students=students, student_name=student_name)


# --- Admin creates users ---
@app.route('/dashboard/admin/create_user', methods=['GET','POST'])
@login_required(role='Admin')
def create_user():
    form = CreateUserForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists!', 'danger')
        else:
            hashed_password = generate_password_hash(form.password.data)
            db.session.add(User(username=form.username.data, password=hashed_password, role=form.role.data))
            db.session.commit()
            flash(f'{form.role.data} account created successfully!', 'success')
            return redirect(url_for('dashboard_admin'))
    return render_template('create_user.html', form=form)

# --- View students ---
@app.route('/dashboard/admin/students')
@app.route('/dashboard/instructor/students')
@login_required(role=['Admin','Instructor'])
def view_students():
    students = Student.query.all()
    return render_template('students.html', students=students)

# --- Add student ---
@app.route('/dashboard/admin/students/add', methods=['GET','POST'])
@app.route('/dashboard/instructor/students/add', methods=['GET','POST'])
@login_required(role=['Admin','Instructor'])
def add_student():
    form = StudentForm()
    if form.validate_on_submit():
        if Student.query.filter_by(student_id=form.student_id.data, subject=form.subject.data).first():
            flash('This student for the same subject already exists!', 'danger')
        else:
            new_student = Student(
                student_id=form.student_id.data,
                name=form.name.data,
                subject=form.subject.data,
                grade=form.grade.data,
                remarks=form.remarks.data
            )
            db.session.add(new_student)

            # Auto-create student user
            if not User.query.filter_by(username=form.student_id.data).first():
                hashed_password = generate_password_hash(form.student_id.data)
                db.session.add(User(
                    username=form.student_id.data,
                    password=hashed_password,
                    role='Student'
                ))

            db.session.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('view_students'))

    return render_template('add_student.html', form=form)

# --- Edit student ---
@app.route('/dashboard/admin/students/edit/<int:student_id>', methods=['GET','POST'])
@app.route('/dashboard/instructor/students/edit/<int:student_id>', methods=['GET','POST'])
@login_required(role=['Admin','Instructor'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    form = StudentForm(obj=student)
    if form.validate_on_submit():
        student.student_id = form.student_id.data
        student.name = form.name.data
        student.subject = form.subject.data
        student.grade = form.grade.data
        student.remarks = form.remarks.data
        db.session.commit()
        flash('Student record updated successfully!', 'success')
        return redirect(url_for('view_students'))
    return render_template('edit_student.html', form=form, student=student)

# --- Bulk Delete ---
@app.route('/dashboard/admin/students/bulk_delete', methods=['POST'])
@app.route('/dashboard/instructor/students/bulk_delete', methods=['POST'])
@login_required(role=['Admin','Instructor'])
def bulk_delete_students():
    student_ids = request.form.getlist('student_ids')
    if student_ids:
        for sid in student_ids:
            student = Student.query.get(int(sid))
            if student:
                db.session.delete(student)
        db.session.commit()
        flash(f'{len(student_ids)} student(s) deleted successfully!', 'success')
    else:
        flash('No students selected for deletion.', 'warning')
    return redirect(url_for('view_students'))

# --- CSV Upload ---
@app.route('/dashboard/admin/students/upload', methods=['GET','POST'])
@app.route('/dashboard/instructor/students/upload', methods=['GET','POST'])
@login_required(role=['Admin','Instructor'])
def upload_students():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            added_count = 0
            skipped_count = 0
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if not Student.query.filter_by(student_id=row['student_id'], subject=row['subject']).first():
                        db.session.add(Student(
                            student_id=row['student_id'],
                            name=row['name'],
                            subject=row['subject'],
                            grade=row.get('grade',''),
                            remarks=row.get('remarks','')
                        ))
                        added_count += 1
                    else:
                        skipped_count += 1
                    if not User.query.filter_by(username=row['student_id']).first():
                        hashed_password = generate_password_hash(row['student_id'])
                        db.session.add(User(
                            username=row['student_id'],
                            password=hashed_password,
                            role='Student'
                        ))
            db.session.commit()
            flash(f'CSV uploaded: {added_count} added, {skipped_count} skipped duplicates', 'success')
            return redirect(url_for('view_students'))
        else:
            flash('Invalid file type. Only CSV allowed.', 'danger')
            return redirect(request.url)
    return render_template('upload_students.html')

# --- Initialize Database ---
with app.app_context():
    db.create_all()

    # Default users with hashed passwords
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password=generate_password_hash('admin123'), role='Admin'))
    if not User.query.filter_by(username='instructor').first():
        db.session.add(User(username='instructor', password=generate_password_hash('instr123'), role='Instructor'))
    if not User.query.filter_by(username='student').first():
        db.session.add(User(username='student', password=generate_password_hash('stud123'), role='Student'))
    db.session.commit()