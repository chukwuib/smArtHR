from app import db
from datetime import datetime
from flask_login import UserMixin # Import UserMixin

class User(db.Model, UserMixin): # Inherit from UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False) # Store hashed passwords
    role = db.Column(db.String(50), nullable=False)  # e.g., 'HR', 'Admin'
    jobs = db.relationship('Job', backref='hr_manager', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(50), nullable=False)  # e.g., 'entry', 'professional', 'expert', 'c-suite'
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hr_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    questions = db.relationship('Question', backref='job', lazy=True)
    applications = db.relationship('Application', backref='job', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), nullable=False)  # e.g., 'objective', 'role-play', 'case-study'
    expected_answer_guideline = db.Column(db.Text, nullable=True)
    answers = db.relationship('Answer', backref='question', lazy=True)

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True) # Allow null initially
    email = db.Column(db.String(120), unique=True, nullable=True) # Allow null initially, still unique when filled
    kyc_details = db.Column(db.Text, nullable=True)  # Store as JSON string or separate fields
    unique_link_token = db.Column(db.String(120), unique=True, nullable=False)
    applications = db.relationship('Application', backref='candidate', lazy=True)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')  # e.g., Pending, Submitted, Graded
    submission_date = db.Column(db.DateTime, nullable=True)
    answers = db.relationship('Answer', backref='application', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=True)
    grading_feedback = db.Column(db.Text, nullable=True)
