from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import secrets # For generating unique tokens
from datetime import datetime # For submission_date
from werkzeug.security import generate_password_hash, check_password_hash # For password hashing

# Initialize SQLAlchemy first, without the app object
db = SQLAlchemy()

# Then create the app
app = Flask(__name__)
app.config.from_object('config') # Load config from config.py
app.config['SECRET_KEY'] = 'your_secret_key' # Add a secret key for session management and WTF-forms

# Now initialize the db with the app
db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Name of the login route

# Import models and forms after app and db are defined to avoid circular imports
from models import User, Job, Question, Candidate, Application, Answer # Ensure all necessary models are imported
from forms import LoginForm, JobForm # Ensure JobForm is imported, ApplicationForm will be added later
from ai_modules import generate_placeholder_questions, grade_application_placeholder # Import AI modules

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('hr_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('hr_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # Using plain text password comparison for now as per instructions for simplicity
        # This should be replaced with hashed password checking in a real app.
        # if user and user.password_hash == form.password.data: # Plain text check
        if user and check_password_hash(user.password_hash, form.password.data): # Hashed password check
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('hr_dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/hr_dashboard')
@login_required
def hr_dashboard():
    # List jobs created by this HR or all jobs if admin (simplified: all jobs for now)
    jobs = Job.query.all()
    # Fetch all applications for now. In a real app, filter by HR or job status.
    applications = Application.query.order_by(Application.submission_date.desc()).all()
    return render_template('hr_dashboard.html', title='HR Dashboard', jobs=jobs, applications=applications)

@app.route('/create_job', methods=['GET', 'POST'])
@login_required
def create_job():
    form = JobForm()
    if form.validate_on_submit():
        job = Job(job_title=form.job_title.data,
                  description=form.description.data,
                  level=form.level.data,
                  hr_id=current_user.id)
        db.session.add(job)
        db.session.commit() # Commit to get job.id

        # Generate and add placeholder questions
        generated_questions = generate_placeholder_questions(job.level, job.job_title)
        for q_data in generated_questions:
            question = Question(job_id=job.id,
                                question_text=q_data['question_text'],
                                question_type=q_data['question_type'])
            db.session.add(question)
        
        db.session.commit() # Commit questions

        flash(f'Job "{job.job_title}" created successfully with {len(generated_questions)} placeholder questions!', 'success')
        return redirect(url_for('hr_dashboard'))
    return render_template('create_job.html', title='Create Job', form=form)

if __name__ == '__main__':
    # Note: The init_db command should be run separately as shown in previous steps.
    # Example: python -c "from app import app, db; from models import User; from werkzeug.security import generate_password_hash; app.app_context().push(); db.create_all(); User.query.delete(); db.session.commit(); new_user = User(username='hr_user', password_hash=generate_password_hash('password', method='pbkdf2:sha256'), role='HR'); db.session.add(new_user); db.session.commit(); print('DB created and user added.')"
    app.run(debug=True)


# --- Candidate Application Routes ---
@app.route('/job/<int:job_id>/create_application', methods=['GET']) # Should be GET as it's creating a resource and then showing a link
@login_required
def create_application_link(job_id):
    job = Job.query.get_or_404(job_id)
    # Ensure the current HR user has permissions for this job if needed (omitted for simplicity)

    token = secrets.token_urlsafe(32)
    
    # Create Candidate (details to be filled by candidate later)
    candidate = Candidate(unique_link_token=token)
    db.session.add(candidate)
    db.session.commit() # Commit to get candidate.id

    # Create Application linking job and candidate
    application = Application(job_id=job.id, candidate_id=candidate.id, status='Pending')
    db.session.add(application)
    db.session.commit()

    application_url = url_for('apply_for_job', token=token, _external=True)
    # For now, just flash the message. Later, use a template.
    # flash(f'Application link generated: {application_url}', 'success')
    # return redirect(url_for('hr_dashboard'))
    return render_template('application_link_generated.html', application_url=application_url, job=job)


@app.route('/application/<int:application_id>/view')
@login_required
def view_application(application_id):
    application = Application.query.get_or_404(application_id)
    # Assuming current_user is HR. Add role/permission checks in a real app.

    # Prepare answers in a dictionary for easy lookup in the template
    answers_map = {answer.question_id: answer for answer in application.answers}
    
    # Ensure questions are typically sorted by ID for consistent display
    job_questions = sorted(application.job.questions, key=lambda q: q.id)

    return render_template('view_application.html', 
                           application=application,
                           candidate=application.candidate,
                           job=application.job,
                           questions=job_questions, # Pass sorted questions
                           answers_map=answers_map)


@app.route('/application/<int:application_id>/grade', methods=['GET', 'POST']) # POST is better if it's an action
@login_required
def grade_application_route(application_id):
    # In a real app, add permission checks: e.g., ensure current_user is HR and can grade this application
    
    # Call the placeholder grading function
    result, status_code = grade_application_placeholder(application_id)

    if status_code == 200:
        flash(result.get("message", "Application graded."), 'success')
    else:
        flash(result.get("error", "Failed to grade application."), 'danger')
        
    return redirect(url_for('hr_dashboard'))


@app.route('/apply/<token>', methods=['GET', 'POST'])
def apply_for_job(token):
    candidate = Candidate.query.filter_by(unique_link_token=token).first_or_404()
    application = Application.query.filter_by(candidate_id=candidate.id).order_by(Application.id.desc()).first() # Get the latest app for this candidate
    
    if not application:
        abort(404, description="Application not found for this token.")
    if application.status == 'Submitted':
        flash('This application has already been submitted.', 'info')
        return render_template('thank_you.html', job_title=application.job.job_title, message="Application Already Submitted")

    job = application.job
    questions = sorted(job.questions, key=lambda q: q.id) # Ensure consistent order

    form = ApplicationForm(request.form) # Pass request.form for POST, otherwise it's empty for GET

    if request.method == 'POST' and form.validate():
        # Update Candidate KYC details
        candidate.name = form.name.data
        candidate.email = form.email.data
        # Potentially add more KYC details here if form is expanded
        db.session.add(candidate)

        # Process answers
        for question in questions:
            answer_text = request.form.get(f'answer_for_q_{question.id}')
            if answer_text is not None:
                # Check if an answer already exists for this question and application
                existing_answer = Answer.query.filter_by(application_id=application.id, question_id=question.id).first()
                if existing_answer:
                    existing_answer.answer_text = answer_text # Update existing answer
                    db.session.add(existing_answer)
                else:
                    new_answer = Answer(application_id=application.id,
                                        question_id=question.id,
                                        answer_text=answer_text)
                    db.session.add(new_answer)
            else:
                # Handle case where an answer might be missing if that's an error
                # For now, we'll assume optional or frontend ensures submission
                pass
        
        application.status = 'Submitted'
        application.submission_date = datetime.utcnow()
        db.session.add(application)
        
        db.session.commit()
        
        flash('Your application has been submitted successfully!', 'success')
        return render_template('thank_you.html', job_title=job.job_title, message="Application Submitted Successfully")

    # For GET request or if form validation fails on POST
    if request.method == 'GET' and candidate.name: # Pre-fill if candidate data exists
        form.name.data = candidate.name
        form.email.data = candidate.email
        
    return render_template('apply.html', 
                           form=form, 
                           candidate=candidate, 
                           application=application, 
                           job=job, 
                           questions=questions,
                           token=token)
