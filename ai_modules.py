# This file will contain AI-related placeholder functions.

def generate_placeholder_questions(job_level, job_title):
    questions = []
    if job_level == 'entry':
        questions.append({'question_text': f"What are your key strengths for an entry-level {job_title} position?", 'question_type': 'objective'})
        questions.append({'question_text': "Describe a challenging project you worked on during your studies.", 'question_type': 'objective'})
        questions.append({'question_text': "Where do you see yourself in 3 years?", 'question_type': 'objective'})
    elif job_level == 'professional':
        questions.append({'question_text': f"Describe a significant achievement in your previous role as a {job_title}.", 'question_type': 'objective'})
        questions.append({'question_text': "How do you handle conflicting priorities in a team project?", 'question_type': 'role-play'})
        questions.append({'question_text': f"What are the latest trends in the {job_title} field?", 'question_type': 'case-study'}) # Simple case study
    elif job_level == 'expert':
        questions.append({'question_text': f"Detail your experience leading complex projects in the {job_title} domain.", 'question_type': 'case-study'})
        questions.append({'question_text': "Imagine you disagree with a key strategic decision in your area of expertise. How would you address this with senior leadership?", 'question_type': 'role-play'})
    elif job_level == 'c-suite':
        questions.append({'question_text': f"Outline your vision for the {job_title} function in a rapidly evolving market.", 'question_type': 'case-study'})
        questions.append({'question_text': "Describe how you would lead organizational change following a major acquisition.", 'question_type': 'role-play'})
    
    # Default question if no specific questions were added (e.g., unknown job_level or empty list for a level)
    if not questions:
         questions.append({'question_text': f"Tell us about yourself and why you are interested in the {job_title} role at the {job_level} level.", 'question_type': 'objective'})
    
    return questions

import random
# It's better to pass db and models if they are needed, rather than importing directly from app,
# to avoid circular dependencies and make the module more reusable.
# However, following instructions to import from app and models directly.
from app import db # Assuming db is accessible from app for commit
from models import Application, Answer

def grade_application_placeholder(application_id):
    application = Application.query.get(application_id)

    if not application:
        return {"error": "Application not found."}, 404
    
    if application.status != 'Submitted':
        return {"error": f"Application status is '{application.status}', not 'Submitted'. Cannot grade."}, 400

    answers = application.answers # Assuming backref 'answers' is defined in Application model

    if not answers:
        application.status = 'Graded' # Or 'GradingError' / 'NoAnswersToGrade'
        db.session.add(application)
        db.session.commit()
        return {"message": "Application has no answers to grade. Status set to 'Graded'.", "application_id": application_id}, 200

    for answer in answers:
        score = random.randint(1, 5)
        answer.score = score
        if score > 3:
            answer.grading_feedback = "Looks promising. Good insights."
        elif score == 3:
            answer.grading_feedback = "Meets expectations, but could be more detailed."
        else:
            answer.grading_feedback = "Lacks detail or clarity. Needs improvement."
        db.session.add(answer)

    application.status = 'Graded'
    db.session.add(application)
    db.session.commit()
    
    return {"message": "Application graded successfully.", "application_id": application_id}, 200
