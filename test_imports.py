"""
Test script to verify all imports are working correctly
Run this before starting the main application
"""

print("=" * 50)
print("Testing Imports for Smart Placement System")
print("=" * 50)

# Test Flask
try:
    from flask import Flask
    print("✓ Flask imported successfully")
except Exception as e:
    print(f"✗ Flask import error: {e}")

# Test Flask-SQLAlchemy
try:
    from flask_sqlalchemy import SQLAlchemy
    print("✓ SQLAlchemy imported successfully")
except Exception as e:
    print(f"✗ SQLAlchemy import error: {e}")

# Test Flask-Login
try:
    from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
    print("✓ Flask-Login imported successfully")
except Exception as e:
    print(f"✗ Flask-Login import error: {e}")

# Test Flask-WTF
try:
    from flask_wtf import FlaskForm
    from flask_wtf.file import FileField, FileAllowed
    print("✓ Flask-WTF imported successfully")
except Exception as e:
    print(f"✗ Flask-WTF import error: {e}")

# Test WTForms
try:
    from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FloatField, IntegerField, SelectField, DateTimeField
    from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange
    print("✓ WTForms imported successfully")
except Exception as e:
    print(f"✗ WTForms import error: {e}")

# Test config
try:
    from config import config
    print("✓ Config imported successfully")
except Exception as e:
    print(f"✗ Config import error: {e}")

# Test models
try:
    from models import db, User, StudentProfile, Company, PlacementDrive, Application, Notification
    print("✓ Models imported successfully")
except Exception as e:
    print(f"✗ Models import error: {e}")

# Test forms
try:
    from forms import LoginForm, RegistrationForm, StudentProfileForm, CompanyForm, PlacementDriveForm
    print("✓ Forms imported successfully")
except Exception as e:
    print(f"✗ Forms import error: {e}")

# Test Python built-in modules
try:
    import os
    import uuid
    from datetime import datetime
    from werkzeug.utils import secure_filename
    print("✓ Python built-in modules imported successfully")
except Exception as e:
    print(f"✗ Built-in modules import error: {e}")

print("\n" + "=" * 50)
print("Import testing completed!")
print("=" * 50)
print("\nIf all checks show ✓, you can run: python app.py")
print("If any ✗ appears, check the error messages above.")