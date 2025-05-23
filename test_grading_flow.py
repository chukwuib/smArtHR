from app import app, db
from models import User, Job, Question, Candidate, Application, Answer
from ai_modules import generate_placeholder_questions, grade_application_placeholder
from werkzeug.security import generate_password_hash
from datetime import datetime
import secrets
import random

def setup_for_grading_test():
    """
    Sets up the database with a submitted application ready for grading.
    This function reuses and adapts logic from test_candidate_application_flow.py
    """
    print("Setting up data for grading test...")
    
    # --- Force drop and recreate all tables ---
    db.drop_all()
    db.create_all()

    # --- HR User ---
    hr_user = User.query.filter_by(username='hr_user_grading').first()
    if not hr_user:
        hr_user = User(username='hr_user_grading', password_hash=generate_password_hash('password', method='pbkdf2:sha256'), role='HR')
        db.session.add(hr_user)
        db.session.commit()

    # --- Job with Questions ---
    job_title = "Grader Job"
    job_level = "professional"
    job = Job.query.filter_by(job_title=job_title).first()
    if not job:
        job = Job(job_title=job_title, description="Job for grading test.", level=job_level, hr_id=hr_user.id)
        db.session.add(job)
        db.session.commit()
        questions_data = generate_placeholder_questions(job.level, job.job_title)
        for q_data in questions_data:
            q = Question(job_id=job.id, question_text=q_data['question_text'], question_type=q_data['question_type'])
            db.session.add(q)
        db.session.commit()
    
    job_questions = Question.query.filter_by(job_id=job.id).all()
    if not job_questions:
        raise Exception("Failed to create questions for the job.")

    # --- Candidate ---
    token = secrets.token_urlsafe(16) # Shorter token for test candidate
    candidate_name = "Grader Candidate"
    candidate_email = f"grader.candidate_{token}@example.com" # Ensure unique email
    
    candidate = Candidate(name=candidate_name, email=candidate_email, unique_link_token=token)
    db.session.add(candidate)
    db.session.commit()

    # --- Application with Answers (Submitted) ---
    application = Application(job_id=job.id, candidate_id=candidate.id, status='Submitted', submission_date=datetime.utcnow())
    db.session.add(application)
    db.session.commit()

    for question in job_questions:
        answer = Answer(application_id=application.id, question_id=question.id, answer_text=f"Test answer to {question.question_text[:30]}...")
        db.session.add(answer)
    db.session.commit()
    
    print(f"Setup complete. Application ID {application.id} for job '{job.job_title}' is 'Submitted' with {len(job_questions)} answers.")
    return application.id


def run_test():
    with app.app_context():
        print("Starting Grading Flow Test...")
        
        try:
            application_id_to_grade = setup_for_grading_test()
        except Exception as e:
            print(f"Error during setup: {e}")
            return

        # --- 1. Simulate HR Triggering Grading ---
        print(f"Simulating HR grading application ID: {application_id_to_grade}")
        
        # Directly call the grading function (as the route would)
        # Ensure random seed for predictable "random" scores if needed for very specific assertions,
        # but for placeholder, current behavior is fine.
        # random.seed(42) # Optional: for reproducible random numbers
        
        result, status_code = grade_application_placeholder(application_id_to_grade)
        
        print(f"Grading function result: {result}, Status Code: {status_code}")

        if status_code != 200:
            print(f"FAIL: Grading function returned an error: {result.get('error', 'Unknown error')}")
            return

        # --- 2. Verify Database State ---
        print("Verifying database state after grading...")
        graded_application = Application.query.get(application_id_to_grade)

        if not graded_application:
            print(f"FAIL: Could not retrieve application ID {application_id_to_grade} after grading.")
            return

        # Application Status Check
        if graded_application.status == 'Graded':
            print(f"PASS: Application status successfully updated to 'Graded'.")
        else:
            print(f"FAIL: Application status is '{graded_application.status}', expected 'Graded'.")
            return # Stop further checks if status is wrong

        # Answers Check (Scores and Feedback)
        answers = graded_application.answers
        if not answers:
            print("WARN: Application has no answers. This might be okay if handled by grading logic, but check setup.")
        else:
            print(f"Checking {len(answers)} answers for scores and feedback...")
            all_answers_graded = True
            for i, answer in enumerate(answers):
                if answer.score is None or answer.grading_feedback is None:
                    print(f"FAIL: Answer {i+1} (ID: {answer.id}) for Question ID {answer.question_id} was not graded (score or feedback missing).")
                    all_answers_graded = False
                    break
                else:
                    print(f"  - Answer ID {answer.id}: Score={answer.score}, Feedback='{answer.grading_feedback[:30]}...'")
            
            if all_answers_graded:
                print("PASS: All answers appear to have scores and feedback.")
            else:
                print("FAIL: Not all answers were fully graded.")
        
        print("Grading Flow Test finished.")

if __name__ == '__main__':
    run_test()
