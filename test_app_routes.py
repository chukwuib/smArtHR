import unittest
from app import app, db # Assuming app, db are from your main app file
from models import User, Job, Question # Question model might be needed if job creation also creates questions
from werkzeug.security import generate_password_hash
# Flask-Login's login_user is for server-side logic, not directly for test client session.
# The test client handles sessions/cookies automatically when it makes requests.

class BasicRouteTests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for simpler testing of form posts
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory SQLite for tests
        # SECRET_KEY is already set in app.py, but good to be aware for testing sessions
        # app.config['SECRET_KEY'] = 'test_secret_key_for_routes' 
        app.config['LOGIN_DISABLED'] = False # Ensure login is not disabled globally if such a config exists

        self.client = app.test_client()
        
        # Establish an application context before creating the database tables.
        self.app_context = app.app_context()
        self.app_context.push() # Push the context
        
        db.create_all()
        
        # Create a test HR user
        password_hash_hr = generate_password_hash('testpasswordhr', method='pbkdf2:sha256')
        self.hr_user = User(username='testhr', password_hash=password_hash_hr, role='HR')
        db.session.add(self.hr_user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop() # Pop the context to clean up

    def login_hr_user(self):
        # Use the test client's post method to the login route
        return self.client.post('/login', data=dict(
            username='testhr',
            password='testpasswordhr' 
        ), follow_redirects=True)

    def logout_user(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_01_unauthenticated_dashboard_access(self):
        print("Running: test_01_unauthenticated_dashboard_access")
        # Ensure logged out (should be by default for a new client, but good practice)
        # self.logout_user() # Not strictly necessary here as each test gets a fresh client context effectively
        response = self.client.get('/hr_dashboard')
        self.assertEqual(response.status_code, 302, "Response should be a redirect for unauthenticated access.")
        self.assertTrue('/login' in response.location, "Redirect location should contain '/login'.")

    def test_02_login_logout(self):
        print("Running: test_02_login_logout")
        # Login
        login_response = self.login_hr_user()
        self.assertEqual(login_response.status_code, 200, "Login should be successful and redirect to dashboard (200).")
        self.assertIn(b'HR Dashboard', login_response.data, "Dashboard content not found after login.")
        self.assertIn(b'Logged in successfully.', login_response.data, "Flash message for login not found.")


        # Check accessing a protected page while logged in
        dashboard_response = self.client.get('/hr_dashboard', follow_redirects=True)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn(b'Welcome, testhr', dashboard_response.data)


        # Logout
        logout_response = self.logout_user()
        self.assertEqual(logout_response.status_code, 200, "Logout should redirect to login page (200).")
        self.assertTrue('/login' in logout_response.request.path or b'Login</title>' in logout_response.data, "Should be on login page after logout.")
        self.assertIn(b'You have been logged out.', logout_response.data, "Flash message for logout not found.")

        # Verify dashboard is protected again
        dashboard_response_after_logout = self.client.get('/hr_dashboard')
        self.assertEqual(dashboard_response_after_logout.status_code, 302)
        self.assertTrue('/login' in dashboard_response_after_logout.location)


    def test_03_authenticated_dashboard_access(self):
        print("Running: test_03_authenticated_dashboard_access")
        self.login_hr_user()
        response = self.client.get('/hr_dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Authenticated dashboard access should return 200.")
        self.assertIn(b'HR Dashboard', response.data, "Dashboard content not found for authenticated user.")
        self.assertIn(b'Welcome, testhr', response.data, "Welcome message for test HR user not found.")
        self.logout_user()

    def test_04_authenticated_create_job_get(self):
        print("Running: test_04_authenticated_create_job_get")
        self.login_hr_user()
        response = self.client.get('/create_job', follow_redirects=True)
        self.assertEqual(response.status_code, 200, "Authenticated GET /create_job should return 200.")
        self.assertIn(b'Create New Job', response.data, "'Create New Job' title not found on page.")
        self.logout_user()

    def test_05_create_job_post_and_verify_questions(self):
        print("Running: test_05_create_job_post_and_verify_questions")
        self.login_hr_user()
        
        initial_job_count = Job.query.count()
        initial_question_count = Question.query.count()

        job_data = {
            'job_title': 'Test Job Title via Route',
            'description': 'A job created by a test route for route testing.',
            'level': 'entry' # Assuming 'entry' level generates specific questions
        }
        
        # Post to create job
        response = self.client.post('/create_job', data=job_data, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200, "POST /create_job should redirect to dashboard (200).")
        # The success message now includes the job title and number of questions.
        # Example: flash(f'Job "{job.job_title}" created successfully with {len(generated_questions)} placeholder questions!', 'success')
        self.assertIn(b'Job &#34;Test Job Title via Route&#34; created successfully with 3 placeholder questions!', response.data, "Success message for job creation not found or incorrect.")
        
        # Verify job count increased
        final_job_count = Job.query.count()
        self.assertEqual(final_job_count, initial_job_count + 1, "Job count should increment by 1.")
        
        # Verify the new job details
        new_job = Job.query.filter_by(job_title=job_data['job_title']).first()
        self.assertIsNotNone(new_job, "Newly created job not found in database.")
        self.assertEqual(new_job.level, job_data['level'], "Job level mismatch for created job.")
        self.assertEqual(new_job.hr_manager.username, 'testhr', "Job HR manager mismatch.")

        # Verify questions were created for this job (entry level should create 3 questions)
        final_question_count = Question.query.count()
        questions_for_new_job = Question.query.filter_by(job_id=new_job.id).all()
        
        # Based on ai_modules.py, entry level jobs get 3 questions
        expected_questions_for_entry = 3
        self.assertEqual(len(questions_for_new_job), expected_questions_for_entry, f"Expected {expected_questions_for_entry} questions for an entry level job.")
        self.assertEqual(final_question_count, initial_question_count + expected_questions_for_entry, "Total question count mismatch.")

        print(f"Job '{new_job.job_title}' created with ID {new_job.id} and {len(questions_for_new_job)} questions.")
        for q_idx, q_obj in enumerate(questions_for_new_job):
            print(f"  Q{q_idx+1}: {q_obj.question_text[:50]}... (Type: {q_obj.question_type})")
            self.assertTrue(job_data['job_title'] in q_obj.question_text or "studies" in q_obj.question_text or "years" in q_obj.question_text)


        self.logout_user()

if __name__ == '__main__':
    # This allows running the tests from the command line
    unittest.main(verbosity=2)
