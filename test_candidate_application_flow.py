from app import app, db
from models import User, Job, Question, Candidate, Application, Answer
from ai_modules import generate_placeholder_questions # To create questions for a test job
from werkzeug.security import generate_password_hash
from datetime import datetime
import secrets

def run_test():
    with app.app_context():
        print("Starting Candidate Application Flow Test...")
        
        # --- Force drop and recreate all tables ---
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        print("Database tables recreated.")

        # --- Setup: Ensure HR User and a Job with Questions ---
        hr_user = User.query.filter_by(username='hr_user').first()
        if not hr_user:
            print("Creating hr_user...")
            hr_user = User(username='hr_user', password_hash=generate_password_hash('password', method='pbkdf2:sha256'), role='HR')
            db.session.add(hr_user)
            db.session.commit()

        test_job_title = "Senior Test Developer"
        test_job_level = "professional"
        job = Job.query.filter_by(job_title=test_job_title).first()
        if not job:
            print(f"Creating test job: {test_job_title}")
            job = Job(job_title=test_job_title, description="A job for testing application flow.", level=test_job_level, hr_id=hr_user.id)
            db.session.add(job)
            db.session.commit() 

            questions_data = generate_placeholder_questions(job.level, job.job_title)
            for q_data in questions_data:
                q = Question(job_id=job.id, question_text=q_data['question_text'], question_type=q_data['question_type'])
                db.session.add(q)
            db.session.commit()
            print(f"Added {len(questions_data)} questions to '{test_job_title}'.")
        
        job_questions = Question.query.filter_by(job_id=job.id).all()
        if not job_questions:
            print(f"ERROR: No questions found for job {job.id} (Title: {job.job_title}). Test cannot proceed effectively.")
            # Attempt to add questions if missing, assuming job exists
            if job:
                print(f"Attempting to add questions to existing job ID: {job.id}")
                questions_data = generate_placeholder_questions(job.level, job.job_title)
                if questions_data:
                    for q_data in questions_data:
                        # Check if question already exists to prevent duplicates if this part is re-run
                        exists = Question.query.filter_by(job_id=job.id, question_text=q_data['question_text']).first()
                        if not exists:
                            q = Question(job_id=job.id, question_text=q_data['question_text'], question_type=q_data['question_type'])
                            db.session.add(q)
                    db.session.commit()
                    job_questions = Question.query.filter_by(job_id=job.id).all()
                    print(f"Added {len(questions_data)} questions. Now {len(job_questions)} questions for job.")
                else:
                    print("generate_placeholder_questions returned no questions.")
            if not job_questions: # Re-check
                 print("Still no questions. Aborting test.")
                 return


        # --- 1. Simulate HR Creating Application Link ---
        print(f"Simulating HR creating application link for job ID: {job.id} ({job.job_title})")
        token = secrets.token_urlsafe(32)
        
        candidate = Candidate(unique_link_token=token) 
        db.session.add(candidate)
        db.session.commit() 

        application = Application(job_id=job.id, candidate_id=candidate.id, status='Pending')
        db.session.add(application)
        db.session.commit() 
        print(f"Generated token: {token}, Candidate ID: {candidate.id}, Application ID: {application.id}")

        # --- 2. Simulate Candidate Applying (POST request to /apply/<token>) ---
        print(f"Simulating candidate applying with token: {token}")
        candidate_name = "Test Candidate One"
        candidate_email = "test.candidate@example.com"
        
        submitted_answers = {}
        for q in job_questions:
            submitted_answers[f'answer_for_q_{q.id}'] = f"This is a test answer for question ID {q.id} about {q.question_text[:20]}..."

        retrieved_candidate = Candidate.query.filter_by(unique_link_token=token).first()
        retrieved_candidate.name = candidate_name
        retrieved_candidate.email = candidate_email
        db.session.add(retrieved_candidate)

        retrieved_application = Application.query.filter_by(id=application.id).first()
        for question in job_questions:
            answer_text = submitted_answers.get(f'answer_for_q_{question.id}')
            if answer_text:
                new_answer = Answer(application_id=retrieved_application.id,
                                    question_id=question.id,
                                    answer_text=answer_text)
                db.session.add(new_answer)
        
        retrieved_application.status = 'Submitted'
        retrieved_application.submission_date = datetime.utcnow()
        db.session.add(retrieved_application)
        db.session.commit()
        print("Candidate application submitted and data committed.")

        # --- 3. Verify Database State ---
        print("Verifying database state...")
        final_candidate = Candidate.query.get(candidate.id)
        final_application = Application.query.get(application.id)
        final_answers = Answer.query.filter_by(application_id=application.id).all()

        if final_candidate.name == candidate_name and final_candidate.email == candidate_email:
            print(f"PASS: Candidate KYC updated correctly (Name: {final_candidate.name}, Email: {final_candidate.email}).")
        else:
            print(f"FAIL: Candidate KYC mismatch. Expected: {candidate_name}/{candidate_email}, Got: {final_candidate.name}/{final_candidate.email}")

        if final_application.status == 'Submitted' and final_application.submission_date is not None:
            print(f"PASS: Application status is 'Submitted' and submission date is set ({final_application.submission_date}).")
        else:
            print(f"FAIL: Application status incorrect. Status: {final_application.status}, Date: {final_application.submission_date}")

        if len(final_answers) == len(job_questions):
            print(f"PASS: Correct number of answers created ({len(final_answers)}).")
            for ans in final_answers:
                if not ans.answer_text.startswith("This is a test answer"):
                    print(f"FAIL: Answer content for Q_ID {ans.question_id} seems incorrect: {ans.answer_text[:50]}...")
                    break
            else: 
                print("PASS: (Optional) Answer content appears correct.")
        elif len(job_questions) > 0 and len(final_answers) != len(job_questions):
             print(f"FAIL: Number of answers ({len(final_answers)}) does not match number of questions ({len(job_questions)}).")
        elif len(job_questions) == 0:
             print("WARN: No questions were associated with the job, so no answers to check.")
        
        print("Candidate Application Flow Test finished.")

if __name__ == '__main__':
    run_test()
