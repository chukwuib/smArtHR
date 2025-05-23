from app import app, db
from models import User, Job, Question, Candidate, Application, Answer
from ai_modules import generate_placeholder_questions, grade_application_placeholder
from werkzeug.security import generate_password_hash
from datetime import datetime
import secrets

def setup_test_data_for_view_flow():
    print("Setting up data for View Application flow test...")
    db.drop_all()
    db.create_all()

    hr_user = User(username='hr_viewer', password_hash=generate_password_hash('password', method='pbkdf2:sha256'), role='HR')
    db.session.add(hr_user)
    db.session.commit()

    job = Job(job_title="View Test Job", description="Job for view application testing.", level="entry", hr_id=hr_user.id)
    db.session.add(job)
    db.session.commit()

    questions_data = generate_placeholder_questions(job.level, job.job_title)
    for q_data in questions_data:
        q = Question(job_id=job.id, question_text=q_data['question_text'], question_type=q_data['question_type'])
        db.session.add(q)
    db.session.commit()
    job_questions = Question.query.filter_by(job_id=job.id).all()

    apps_created = {}

    # 1. Pending Application
    token_pending = secrets.token_urlsafe(16)
    candidate_pending = Candidate(unique_link_token=token_pending) # Name/email initially null
    db.session.add(candidate_pending)
    db.session.commit()
    app_pending = Application(job_id=job.id, candidate_id=candidate_pending.id, status='Pending')
    db.session.add(app_pending)
    db.session.commit()
    apps_created['pending'] = app_pending.id
    print(f"Created Pending Application ID: {app_pending.id}")

    # 2. Submitted Application
    token_submitted = secrets.token_urlsafe(16)
    candidate_submitted = Candidate(name="Submitted Candidate", email=f"submitted_{token_submitted}@example.com", unique_link_token=token_submitted)
    db.session.add(candidate_submitted)
    db.session.commit()
    app_submitted = Application(job_id=job.id, candidate_id=candidate_submitted.id, status='Submitted', submission_date=datetime.utcnow())
    db.session.add(app_submitted)
    db.session.commit()
    for q in job_questions:
        ans = Answer(application_id=app_submitted.id, question_id=q.id, answer_text=f"Answer for Q{q.id} by Submitted Candidate.")
        db.session.add(ans)
    db.session.commit()
    apps_created['submitted'] = app_submitted.id
    print(f"Created Submitted Application ID: {app_submitted.id} with {len(job_questions)} answers.")


    # 3. Graded Application
    token_graded = secrets.token_urlsafe(16)
    candidate_graded = Candidate(name="Graded Candidate", email=f"graded_{token_graded}@example.com", unique_link_token=token_graded)
    db.session.add(candidate_graded)
    db.session.commit()
    app_graded = Application(job_id=job.id, candidate_id=candidate_graded.id, status='Submitted', submission_date=datetime.utcnow()) # Initially submitted
    db.session.add(app_graded)
    db.session.commit()
    for q in job_questions:
        ans = Answer(application_id=app_graded.id, question_id=q.id, answer_text=f"Answer for Q{q.id} by Graded Candidate.")
        db.session.add(ans)
    db.session.commit()
    # Now grade it
    grade_application_placeholder(app_graded.id) # This function changes status to 'Graded' and commits
    apps_created['graded'] = app_graded.id
    # Verify it's graded
    _temp_graded_app = Application.query.get(app_graded.id)
    print(f"Created and Graded Application ID: {app_graded.id}, current status: {_temp_graded_app.status}")


    print("Test data setup complete.")
    return apps_created, job.id

def run_test():
    with app.app_context():
        print("Starting View Application Flow Test...")
        try:
            application_ids, job_id_for_test = setup_test_data_for_view_flow()
        except Exception as e:
            print(f"Error during setup: {e}")
            import traceback
            traceback.print_exc()
            return

        job_questions = sorted(Question.query.filter_by(job_id=job_id_for_test).all(), key=lambda q: q.id)

        # Test Case 1: Pending Application
        print("\n--- Testing Pending Application ---")
        app_pending_id = application_ids['pending']
        app_pending = Application.query.get(app_pending_id)
        answers_map_pending = {answer.question_id: answer for answer in app_pending.answers}
        
        assert app_pending.status == 'Pending', f"Pending App Status: Expected 'Pending', got '{app_pending.status}'"
        print(f"PASS: Pending App Status is 'Pending'. Candidate: {app_pending.candidate.name}") # Expect None or empty
        
        found_any_answer_for_pending = False
        for q in job_questions:
            if answers_map_pending.get(q.id):
                found_any_answer_for_pending = True
                break
        assert not found_any_answer_for_pending, "FAIL: Pending application should have no answers in answers_map."
        print("PASS: Pending application has no answers in answers_map as expected.")


        # Test Case 2: Submitted (but not Graded) Application
        print("\n--- Testing Submitted Application ---")
        app_submitted_id = application_ids['submitted']
        app_submitted = Application.query.get(app_submitted_id)
        answers_map_submitted = {answer.question_id: answer for answer in app_submitted.answers}

        assert app_submitted.status == 'Submitted', f"Submitted App Status: Expected 'Submitted', got '{app_submitted.status}'"
        print(f"PASS: Submitted App Status is 'Submitted'. Candidate: {app_submitted.candidate.name}")
        assert len(app_submitted.answers) == len(job_questions), \
            f"FAIL: Submitted app should have {len(job_questions)} answers, found {len(app_submitted.answers)}"
        print(f"PASS: Submitted application has {len(app_submitted.answers)} answers.")

        for q in job_questions:
            answer = answers_map_submitted.get(q.id)
            assert answer is not None, f"FAIL: Submitted app missing answer for Q_ID {q.id}"
            assert answer.answer_text is not None, f"FAIL: Submitted app answer_text is None for Q_ID {q.id}"
            assert answer.score is None, f"FAIL: Submitted app score should be None for Q_ID {q.id}, got {answer.score}"
            assert answer.grading_feedback is None, f"FAIL: Submitted app feedback should be None for Q_ID {q.id}, got {answer.grading_feedback}"
        print("PASS: Submitted application's answers have text, but no scores/feedback, as expected.")

        # Test Case 3: Graded Application
        print("\n--- Testing Graded Application ---")
        app_graded_id = application_ids['graded']
        app_graded = Application.query.get(app_graded_id) # Re-fetch to be sure
        answers_map_graded = {answer.question_id: answer for answer in app_graded.answers}
        
        assert app_graded.status == 'Graded', f"Graded App Status: Expected 'Graded', got '{app_graded.status}'"
        print(f"PASS: Graded App Status is 'Graded'. Candidate: {app_graded.candidate.name}")
        assert len(app_graded.answers) == len(job_questions), \
            f"FAIL: Graded app should have {len(job_questions)} answers, found {len(app_graded.answers)}"
        print(f"PASS: Graded application has {len(app_graded.answers)} answers.")

        for q in job_questions:
            answer = answers_map_graded.get(q.id)
            assert answer is not None, f"FAIL: Graded app missing answer for Q_ID {q.id}"
            assert answer.answer_text is not None, f"FAIL: Graded app answer_text is None for Q_ID {q.id}"
            assert answer.score is not None, f"FAIL: Graded app score should not be None for Q_ID {q.id}"
            assert answer.grading_feedback is not None, f"FAIL: Graded app feedback should not be None for Q_ID {q.id}"
            print(f"  Q_ID {q.id}: Score={answer.score}, Feedback='{answer.grading_feedback[:20]}...'")
        print("PASS: Graded application's answers have text, scores, and feedback, as expected.")

        print("\nView Application Flow Test finished successfully.")

if __name__ == '__main__':
    run_test()
