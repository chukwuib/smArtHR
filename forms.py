from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class JobForm(FlaskForm):
    job_title = StringField('Job Title', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[DataRequired()])
    level = SelectField('Level',
                        choices=[('entry', 'Entry Level'),
                                 ('professional', 'Professional'),
                                 ('expert', 'Expert'),
                                 ('c-suite', 'C-Suite')],
                        validators=[DataRequired()])
    submit = SubmitField('Create Job')

class ApplicationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email Address', validators=[DataRequired(), Length(min=6, max=120)]) # Basic email validation can be added
    # Answer fields will be added dynamically in the route/template
    submit = SubmitField('Submit Application')
