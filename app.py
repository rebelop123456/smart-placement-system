from flask import Flask, render_template, redirect, url_for, flash, request, session, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import uuid
import sqlite3

# Import models
from models import db, User, StudentProfile, Company, PlacementDrive, Application, Notification

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'resumes'), exist_ok=True)

# ========== CONTEXT PROCESSOR ==========
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# ========== USER LOADER ==========
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== HELPER FUNCTIONS ==========
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_file(file, folder='resumes'):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        os.makedirs(folder_path, exist_ok=True)
        filepath = os.path.join(folder_path, unique_filename)
        file.save(filepath)
        return os.path.join(folder, unique_filename)
    return None

def create_notification(user_id, title, message):
    notification = Notification(user_id=user_id, title=title, message=message)
    db.session.add(notification)
    db.session.commit()

def parse_datetime(dt_str):
    """Parse datetime string from form input (HTML datetime-local format)"""
    if not dt_str:
        return None
    dt_str = dt_str.replace('T', ' ')
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M')

def get_eligible_students_for_drive(drive_id):
    """Get all students eligible for a specific drive"""
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return []
    
    company = drive.company
    eligible_students = []
    
    students = StudentProfile.query.filter_by(is_profile_complete=True).all()
    
    for student in students:
        cgpa_eligible = True
        if company.min_cgpa and company.min_cgpa > 0:
            if not student.cgpa or student.cgpa < company.min_cgpa:
                cgpa_eligible = False
        
        branch_eligible = True
        if company.eligible_branches:
            if not student.branch or student.branch not in company.get_eligible_branches_list():
                branch_eligible = False
        
        if cgpa_eligible and branch_eligible:
            eligible_students.append(student)
    
    return eligible_students

def send_drive_notifications_to_eligible_students(drive):
    """Send notifications to all eligible students about new drive"""
    eligible_students = get_eligible_students_for_drive(drive.id)
    
    for student in eligible_students:
        create_notification(
            student.user_id,
            f'New Drive: {drive.title}',
            f'You are eligible for {drive.title} at {drive.company.name}. Apply before {drive.application_deadline.strftime("%Y-%m-%d")}!'
        )
    
    return len(eligible_students)

# ========== AUTHENTICATION ROUTES ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if user.role != role:
                flash(f'This account is for {user.role}s. Please use the correct login option.', 'danger')
                return render_template('login.html')
            
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        roll_number = request.form.get('roll_number')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        role = request.form.get('role', 'student')

        # Prevent admin registration through public form
        if role == 'admin':
            flash('Admin registration is not allowed. Only existing admins can add new admins.', 'danger')
            return redirect(url_for('login'))

        if password != confirm:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')

        # Create user (only student role allowed here)
        user = User(email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create student profile
        profile = StudentProfile(
            user_id=user.id,
            full_name=full_name,
            roll_number=roll_number,
            is_profile_complete=False
        )
        db.session.add(profile)
        db.session.commit()
        create_notification(user.id, 'Welcome!', f'Welcome {full_name}! Complete your profile to start applying.')
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

# ========== STUDENT ROUTES ==========
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))

    profile = current_user.student_profile
    applications = Application.query.filter_by(student_id=profile.id).all()
    
    eligible_drives = []
    if profile.cgpa and profile.branch:
        drives = PlacementDrive.query.filter(
            PlacementDrive.is_active == True,
            PlacementDrive.application_deadline > datetime.utcnow()
        ).all()
        for drive in drives:
            company = drive.company
            cgpa_eligible = True
            if company.min_cgpa and company.min_cgpa > 0:
                if not profile.cgpa or profile.cgpa < company.min_cgpa:
                    cgpa_eligible = False
            
            branch_eligible = True
            if company.eligible_branches:
                if not profile.branch or profile.branch not in company.get_eligible_branches_list():
                    branch_eligible = False
            
            if cgpa_eligible and branch_eligible:
                eligible_drives.append(drive)

    stats = {
        'total_applications': len(applications)
    }
    
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return render_template('dashboard/student_dashboard.html',
                         profile=profile,
                         applications=applications,
                         eligible_drives=eligible_drives,
                         stats=stats,
                         unread_notifications=unread_notifications)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))

    profile = current_user.student_profile

    completion_fields = [
        profile.full_name, profile.roll_number, profile.course, 
        profile.branch, profile.cgpa, profile.graduation_year, 
        profile.phone, profile.skills, profile.resume_path
    ]
    filled_fields = sum(1 for field in completion_fields if field)
    completion = int((filled_fields / len(completion_fields)) * 100) if completion_fields else 0

    if request.method == 'POST':
        profile.full_name = request.form.get('full_name')
        profile.roll_number = request.form.get('roll_number')
        profile.course = request.form.get('course')
        profile.branch = request.form.get('branch')
        profile.cgpa = float(request.form.get('cgpa')) if request.form.get('cgpa') else None
        profile.graduation_year = int(request.form.get('graduation_year')) if request.form.get('graduation_year') else None
        profile.phone = request.form.get('phone')
        profile.skills = request.form.get('skills')
        profile.github = request.form.get('github')
        profile.linkedin = request.form.get('linkedin')
        profile.is_profile_complete = True
        
        if 'resume' in request.files and request.files['resume'].filename:
            resume_path = save_file(request.files['resume'], 'resumes')
            if resume_path:
                profile.resume_path = resume_path
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('placement/profile.html', profile=profile, completion=completion)

@app.route('/student/jobs')
@login_required
def student_jobs():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    
    profile = current_user.student_profile
    drives = PlacementDrive.query.filter(
        PlacementDrive.is_active == True,
        PlacementDrive.application_deadline > datetime.utcnow()
    ).all()
    
    eligible_drives = []
    for drive in drives:
        company = drive.company
        cgpa_eligible = True
        if company.min_cgpa and company.min_cgpa > 0:
            if not profile.cgpa or profile.cgpa < company.min_cgpa:
                cgpa_eligible = False
        
        branch_eligible = True
        if company.eligible_branches:
            if not profile.branch or profile.branch not in company.get_eligible_branches_list():
                branch_eligible = False
        
        if cgpa_eligible and branch_eligible:
            eligible_drives.append(drive)
    
    return render_template('student/jobs.html', drives=eligible_drives)

@app.route('/student/notifications')
@login_required
def student_notifications():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('student/notifications.html', notifications=notifications)

@app.route('/student/drives')
@login_required
def student_drives():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    
    drives = PlacementDrive.query.filter(
        PlacementDrive.is_active == True,
        PlacementDrive.application_deadline > datetime.utcnow()
    ).order_by(PlacementDrive.drive_date).all()
    
    return render_template('student/drives.html', drives=drives)

@app.route('/student/applications')
@login_required
def student_applications():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    
    profile = current_user.student_profile
    applications = Application.query.filter_by(student_id=profile.id).order_by(Application.applied_at.desc()).all()
    
    return render_template('student/applications.html', applications=applications)

@app.route('/mark_notification_read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id == current_user.id:
        notification.is_read = True
        db.session.commit()
        flash('Notification marked as read', 'success')
    return redirect(url_for('student_notifications'))

@app.route('/mark_all_notifications_read')
@login_required
def mark_all_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    flash('All notifications marked as read!', 'success')
    return redirect(url_for('student_notifications'))

@app.route('/apply/<int:drive_id>')
@login_required
def apply_for_drive(drive_id):
    if current_user.role != 'student':
        flash('Only students can apply.', 'danger')
        return redirect(url_for('dashboard'))

    drive = PlacementDrive.query.get_or_404(drive_id)
    profile = current_user.student_profile

    if not profile.is_profile_complete:
        flash('Please complete your profile before applying.', 'warning')
        return redirect(url_for('student_profile'))

    company = drive.company
    
    cgpa_eligible = True
    if company.min_cgpa and company.min_cgpa > 0:
        if not profile.cgpa or profile.cgpa < company.min_cgpa:
            cgpa_eligible = False
    
    branch_eligible = True
    if company.eligible_branches:
        if not profile.branch or profile.branch not in company.get_eligible_branches_list():
            branch_eligible = False
    
    if not cgpa_eligible:
        flash(f'Your CGPA {profile.cgpa} is below required {company.min_cgpa}', 'danger')
        return redirect(url_for('student_drives'))
    
    if not branch_eligible:
        flash('Your branch is not eligible for this drive', 'danger')
        return redirect(url_for('student_drives'))

    existing = Application.query.filter_by(student_id=profile.id, drive_id=drive_id).first()
    if existing:
        flash('You have already applied for this drive', 'warning')
        return redirect(url_for('student_applications'))

    application = Application(student_id=profile.id, drive_id=drive_id, status='eligible')
    db.session.add(application)
    db.session.commit()
    
    create_notification(current_user.id, 'Application Submitted', 
                       f'Your application for {drive.title} at {drive.company.name} has been submitted successfully!')
    
    create_notification(1, 'New Application', f'{profile.full_name} applied for {drive.title}')
    
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('student_applications'))

# ========== ADMIN ROUTES ==========
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))

    from sqlalchemy import func
    
    total_students = StudentProfile.query.count()
    
    # Get students by status
    placed_students = db.session.query(Application.student_id).filter(
        Application.status == 'placed'
    ).distinct().count()
    
    shortlisted_students = db.session.query(Application.student_id).filter(
        Application.status == 'shortlisted'
    ).distinct().count()
    
    selected_students = db.session.query(Application.student_id).filter(
        Application.status == 'selected'
    ).distinct().count()
    
    placement_rate = round((placed_students / total_students * 100) if total_students > 0 else 0, 1)
    
    stats = {
        'total_students': total_students,
        'placed_students': placed_students,
        'shortlisted_students': shortlisted_students,
        'selected_students': selected_students,
        'placement_rate': placement_rate,
        'total_companies': Company.query.count(),
        'total_applications': Application.query.count(),
        'active_drives': PlacementDrive.query.filter_by(is_active=True).count(),
        'pending_applications': Application.query.filter_by(status='eligible').count()
    }
    
    # Get lists of students by status
    placed_students_list = db.session.query(
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        Company.name.label('company_name')
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .filter(Application.status == 'placed')\
     .all()
    
    shortlisted_students_list = db.session.query(
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        Application.interview_date,
        Company.name.label('company_name')
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .filter(Application.status == 'shortlisted')\
     .all()
    
    selected_students_list = db.session.query(
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        Company.name.label('company_name')
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .filter(Application.status == 'selected')\
     .all()
    
    # Top companies by placements
    top_companies = []
    companies = Company.query.all()
    for company in companies:
        placed_count = 0
        for drive in company.drives:
            for app in drive.applications:
                if app.status == 'placed':
                    placed_count += 1
        if placed_count > 0:
            top_companies.append({'name': company.name, 'application_count': placed_count})
    
    top_companies.sort(key=lambda x: x['application_count'], reverse=True)
    top_companies = top_companies[:5]
    
    recent_applications = Application.query.order_by(Application.applied_at.desc()).limit(10).all()
    
    return render_template('dashboard/admin_dashboard.html', 
                         stats=stats,
                         placed_students_list=placed_students_list,
                         shortlisted_students_list=shortlisted_students_list,
                         selected_students_list=selected_students_list,
                         recent_applications=recent_applications,
                         top_companies=top_companies)

@app.route('/admin/add_admin', methods=['GET', 'POST'])
@login_required
def add_admin():
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if not full_name or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('admin/add_admin.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return render_template('admin/add_admin.html')
        
        if password != confirm:
            flash('Passwords do not match', 'danger')
            return render_template('admin/add_admin.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('admin/add_admin.html')
        
        # Create new admin user
        admin = User(email=email, role='admin')
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        
        # Send notification to the new admin
        create_notification(admin.id, 'Admin Account Created', 
                           f'Welcome {full_name}! You have been added as an administrator. Login using your email and password.')
        
        flash(f'Admin "{full_name}" created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_admin.html')

@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    students = StudentProfile.query.order_by(StudentProfile.created_at.desc()).all()
    return render_template('admin/manage_students.html', students=students)

@app.route('/admin/placed_students')
@login_required
def admin_placed_students():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    placed_students = db.session.query(
        StudentProfile.id,
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        StudentProfile.phone,
        PlacementDrive.title.label('drive_name'),
        Company.name.label('company_name'),
        Application.interview_date,
        Application.applied_at
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .filter(Application.status == 'placed')\
     .order_by(Application.interview_date.desc()).all()
    
    return render_template('admin/placed_students.html', placed_students=placed_students)

@app.route('/admin/shortlisted_students')
@login_required
def admin_shortlisted_students():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    shortlisted_students = db.session.query(
        StudentProfile.id,
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        StudentProfile.phone,
        PlacementDrive.title.label('drive_name'),
        Company.name.label('company_name'),
        Application.interview_date,
        Application.applied_at
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .filter(Application.status == 'shortlisted')\
     .order_by(Application.interview_date.desc()).all()
    
    return render_template('admin/shortlisted_students.html', shortlisted_students=shortlisted_students)

@app.route('/admin/selected_students')
@login_required
def admin_selected_students():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    selected_students = db.session.query(
        StudentProfile.id,
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        StudentProfile.phone,
        PlacementDrive.title.label('drive_name'),
        Company.name.label('company_name'),
        Application.applied_at
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .filter(Application.status == 'selected')\
     .order_by(Application.applied_at.desc()).all()
    
    return render_template('admin/selected_students.html', selected_students=selected_students)

@app.route('/admin/registered_students')
@login_required
def admin_registered_students():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    registered_students = db.session.query(
        StudentProfile.id,
        StudentProfile.full_name,
        StudentProfile.roll_number,
        StudentProfile.branch,
        StudentProfile.cgpa,
        StudentProfile.phone,
        StudentProfile.skills,
        PlacementDrive.title.label('drive_name'),
        PlacementDrive.id.label('drive_id'),
        Company.name.label('company_name'),
        Application.status,
        Application.applied_at,
        User.email
    ).join(Application, Application.student_id == StudentProfile.id)\
     .join(PlacementDrive, PlacementDrive.id == Application.drive_id)\
     .join(Company, Company.id == PlacementDrive.company_id)\
     .join(User, User.id == StudentProfile.user_id)\
     .order_by(Application.applied_at.desc()).all()
    
    students_dict = {}
    for student in registered_students:
        if student.id not in students_dict:
            students_dict[student.id] = {
                'id': student.id,
                'full_name': student.full_name,
                'roll_number': student.roll_number,
                'branch': student.branch,
                'cgpa': student.cgpa,
                'phone': student.phone,
                'skills': student.skills,
                'email': student.email,
                'applications': []
            }
        students_dict[student.id]['applications'].append({
            'drive_name': student.drive_name,
            'drive_id': student.drive_id,
            'company_name': student.company_name,
            'status': student.status,
            'applied_at': student.applied_at
        })
    
    students_list = list(students_dict.values())
    
    return render_template('admin/registered_students.html', students=students_list)

@app.route('/admin/companies', methods=['GET', 'POST'])
@login_required
def admin_companies():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        company = Company(
            name=request.form.get('name'),
            description=request.form.get('description'),
            industry=request.form.get('industry'),
            location=request.form.get('location'),
            min_cgpa=float(request.form.get('min_cgpa')) if request.form.get('min_cgpa') else 0,
            eligible_branches=request.form.get('eligible_branches')
        )
        db.session.add(company)
        db.session.commit()
        flash('Company added successfully!', 'success')
        return redirect(url_for('admin_companies'))

    companies = Company.query.order_by(Company.created_at.desc()).all()
    return render_template('admin/manage_companies.html', companies=companies)

@app.route('/admin/drives', methods=['GET', 'POST'])
@login_required
def admin_drives():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))

    companies = Company.query.filter_by(is_active=True).all()
    total_students = StudentProfile.query.count()

    if request.method == 'POST':
        application_deadline = parse_datetime(request.form.get('application_deadline'))
        drive_date = parse_datetime(request.form.get('drive_date'))
        
        drive = PlacementDrive(
            company_id=int(request.form.get('company_id')),
            title=request.form.get('title'),
            description=request.form.get('description'),
            location=request.form.get('location'),
            package=request.form.get('package'),
            positions=int(request.form.get('positions')) if request.form.get('positions') else None,
            application_deadline=application_deadline,
            drive_date=drive_date
        )
        db.session.add(drive)
        db.session.commit()
        
        eligible_count = send_drive_notifications_to_eligible_students(drive)
        
        flash(f'Placement drive created successfully! {eligible_count} eligible students have been notified.', 'success')
        return redirect(url_for('admin_drives'))

    drives = PlacementDrive.query.order_by(PlacementDrive.created_at.desc()).all()
    
    for drive in drives:
        drive.eligible_students = get_eligible_students_for_drive(drive.id)
        drive.eligible_count = len(drive.eligible_students)
    
    return render_template('admin/create_drive.html', 
                         companies=companies, 
                         drives=drives, 
                         total_students=total_students)

@app.route('/admin/applications')
@login_required
def admin_applications():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    applications = Application.query.order_by(Application.applied_at.desc()).all()
    return render_template('placement/applications.html', applications=applications)

@app.route('/admin/update_application/<int:app_id>/<status>')
@login_required
def update_application(app_id, status):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    app_obj = Application.query.get_or_404(app_id)
    app_obj.status = status
    
    if status == 'shortlisted':
        app_obj.interview_date = datetime.utcnow()
        create_notification(app_obj.student.user_id, 'Interview Shortlisted', 
                           f'Congratulations! You have been shortlisted for {app_obj.drive.title} at {app_obj.drive.company.name}. Your interview will be scheduled soon.')
    elif status == 'selected':
        create_notification(app_obj.student.user_id, 'Selection Confirmation', 
                           f'Congratulations! You have been selected for {app_obj.drive.title} at {app_obj.drive.company.name}. Offer letter will be sent shortly.')
    elif status == 'placed':
        create_notification(app_obj.student.user_id, 'Placement Confirmed', 
                           f'Congratulations! You have been placed at {app_obj.drive.company.name}. Welcome to the team!')
    
    db.session.commit()
    
    flash(f'Application status updated to {status}', 'success')
    return redirect(url_for('admin_applications'))

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    from sqlalchemy import func
    
    total_students = StudentProfile.query.count()
    placed_students = db.session.query(Application.student_id).filter(
        Application.status == 'placed'
    ).distinct().count()
    not_placed_students = total_students - placed_students
    placement_rate = round((placed_students / total_students * 100) if total_students > 0 else 0, 1)
    
    stats = {
        'total_students': total_students,
        'placed_students': placed_students,
        'not_placed_students': not_placed_students,
        'placement_rate': placement_rate,
        'total_companies': Company.query.count(),
        'total_drives': PlacementDrive.query.count(),
        'total_applications': Application.query.count()
    }
    
    application_status = db.session.query(
        Application.status, 
        func.count(Application.id).label('count')
    ).group_by(Application.status).all()
    
    top_companies = []
    companies = Company.query.all()
    for company in companies:
        app_count = 0
        for drive in company.drives:
            app_count += len(drive.applications)
        top_companies.append({'name': company.name, 'application_count': app_count})
    
    top_companies.sort(key=lambda x: x['application_count'], reverse=True)
    top_companies = top_companies[:5]
    
    return render_template('admin/reports.html', stats=stats, application_status=application_status, top_companies=top_companies)

@app.route('/admin/delete_company/<int:company_id>')
@login_required
def delete_company(company_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    company = Company.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    flash('Company deleted successfully!', 'success')
    return redirect(url_for('admin_companies'))

@app.route('/admin/delete_drive/<int:drive_id>')
@login_required
def delete_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    drive = PlacementDrive.query.get_or_404(drive_id)
    db.session.delete(drive)
    db.session.commit()
    flash('Drive deleted successfully!', 'success')
    return redirect(url_for('admin_drives'))

@app.route('/admin/drive_eligible_students/<int:drive_id>')
@login_required
def drive_eligible_students(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    drive = PlacementDrive.query.get_or_404(drive_id)
    eligible_students = get_eligible_students_for_drive(drive_id)
    
    return render_template('admin/eligible_students.html', drive=drive, students=eligible_students)

@app.route('/download_resume/<int:student_id>')
@login_required
def download_resume(student_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    student = StudentProfile.query.get_or_404(student_id)
    if student.resume_path:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], student.resume_path)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=f"{student.full_name}_resume.pdf")
    
    flash('Resume not found.', 'danger')
    return redirect(request.referrer or url_for('admin_students'))

@app.route('/admin/database_viewer')
@login_required
def database_viewer():
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    students = StudentProfile.query.all()
    companies = Company.query.all()
    drives = PlacementDrive.query.all()
    applications = Application.query.all()
    notifications = Notification.query.all()
    
    stats = {
        'total_users': len(users),
        'total_students': len(students),
        'total_admins': len([u for u in users if u.role == 'admin']),
        'total_companies': len(companies),
        'total_drives': len(drives),
        'total_applications': len(applications),
        'total_notifications': len(notifications),
        'placed_students': len([a for a in applications if a.status == 'placed']),
        'eligible_students': len([s for s in students if s.is_profile_complete])
    }
    
    return render_template('database_viewer.html', 
                         users=users, 
                         students=students, 
                         companies=companies,
                         drives=drives,
                         applications=applications,
                         notifications=notifications,
                         stats=stats)

# ========== INITIAL DATABASE SETUP ==========
with app.app_context():
    db.create_all()
    
    # Create admin user if not exists
    if not User.query.filter_by(email='admin@placement.com').first():
        admin = User(email='admin@placement.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created: admin@placement.com / admin123")

    # Add sample company if none exist
    if not Company.query.first():
        sample_company = Company(
            name="Tech Innovations Inc.",
            description="Leading technology company specializing in AI and cloud solutions",
            industry="IT",
            location="Bangalore",
            min_cgpa=7.5,
            eligible_branches="CS,IT,ECE"
        )
        db.session.add(sample_company)
        db.session.commit()
        print("✓ Sample company added")
    
    # Add sample drive if none exist
    if not PlacementDrive.query.first() and Company.query.first():
        sample_drive = PlacementDrive(
            company_id=1,
            title="Campus Recruitment 2025",
            description="Exciting opportunities for fresh graduates",
            location="Bangalore",
            package="12-15",
            positions=10,
            application_deadline=datetime(2025, 12, 31, 23, 59),
            drive_date=datetime(2026, 1, 15, 10, 0)
        )
        db.session.add(sample_drive)
        db.session.commit()
        print("✓ Sample drive added")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)