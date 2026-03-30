from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True)
    course = db.Column(db.String(50))
    branch = db.Column(db.String(50))
    cgpa = db.Column(db.Float)
    graduation_year = db.Column(db.Integer)
    phone = db.Column(db.String(15))
    skills = db.Column(db.Text)
    resume_path = db.Column(db.String(200))
    github = db.Column(db.String(200))
    linkedin = db.Column(db.String(200))
    is_profile_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    applications = db.relationship('Application', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<StudentProfile {self.full_name}>'

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    industry = db.Column(db.String(50))
    location = db.Column(db.String(100))
    min_cgpa = db.Column(db.Float, default=0)
    eligible_branches = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    drives = db.relationship('PlacementDrive', backref='company', lazy=True, cascade='all, delete-orphan')
    
    def get_eligible_branches_list(self):
        if self.eligible_branches:
            return [b.strip() for b in self.eligible_branches.split(',') if b.strip()]
        return []
    
    def __repr__(self):
        return f'<Company {self.name}>'

class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    package = db.Column(db.String(50))
    positions = db.Column(db.Integer)
    application_deadline = db.Column(db.DateTime, nullable=False)
    drive_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    applications = db.relationship('Application', backref='drive', lazy=True, cascade='all, delete-orphan')
    
    def is_application_open(self):
        return self.is_active and datetime.utcnow() < self.application_deadline
    
    def __repr__(self):
        return f'<PlacementDrive {self.title}>'

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    status = db.Column(db.String(20), default='eligible')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    interview_date = db.Column(db.DateTime)
    
    __table_args__ = (db.UniqueConstraint('student_id', 'drive_id', name='unique_application'),)
    
    def __repr__(self):
        return f'<Application {self.id}: {self.status}>'

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title}>'