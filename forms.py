from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, IntegerField, SelectField, DateTimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange
from datetime import datetime

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    roll_number = StringField('Roll Number', validators=[DataRequired(), Length(min=5, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class StudentProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    roll_number = StringField('Roll Number', validators=[DataRequired()])
    branch = SelectField('Branch', choices=[
        ('', 'Select Branch'),
        ('CS', 'Computer Science'),
        ('IT', 'Information Technology'),
        ('ECE', 'Electronics & Communication'),
        ('EE', 'Electrical Engineering'),
        ('ME', 'Mechanical Engineering'),
        ('CE', 'Civil Engineering')
    ], validators=[DataRequired()])
    cgpa = FloatField('CGPA', validators=[DataRequired(), NumberRange(min=0, max=10)])
    graduation_year = IntegerField('Graduation Year', validators=[DataRequired(), NumberRange(min=2024, max=2030)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    skills = TextAreaField('Skills (comma-separated)', validators=[DataRequired()])
    resume = FileField('Resume (PDF/DOC)', validators=[FileAllowed(['pdf', 'doc', 'docx'], 'Only PDF and DOC files allowed!')])
    submit = SubmitField('Update Profile')

class CompanyForm(FlaskForm):
    name = StringField('Company Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    industry = StringField('Industry', validators=[DataRequired()])
    website = StringField('Website')
    location = StringField('Location')
    min_cgpa = FloatField('Minimum CGPA', validators=[DataRequired(), NumberRange(min=0, max=10)])
    eligible_branches = StringField('Eligible Branches (comma-separated)', validators=[DataRequired()])
    submit = SubmitField('Add Company')

class PlacementDriveForm(FlaskForm):
    company_id = SelectField('Company', coerce=int, validators=[DataRequired()])
    title = StringField('Drive Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    application_deadline = DateTimeField('Application Deadline', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    drive_date = DateTimeField('Drive Date', format='%Y-%m-%d %H:%M')
    location = StringField('Location')
    package = StringField('Package (LPA)')
    positions = IntegerField('Number of Positions')
    requirements = TextAreaField('Additional Requirements')
    submit = SubmitField('Create Drive')