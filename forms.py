from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError


class RegistrationForm(FlaskForm):
    username = StringField('Username', 
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = EmailField('Email', 
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                             validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        from models import User

        if User.query.filter_by(username=username.data).first():
            raise ValidationError('That username is already taken.')

    def validate_email(self, email):
        from models import User

        if User.query.filter_by(email=email.data.lower()).first():
            raise ValidationError('That email is already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                             validators=[DataRequired(), Length(max=128)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = EmailField('Email',
                       validators=[DataRequired(), Email()])
    picture = FileField('Update profile picture',
                        validators=[FileAllowed(['jpg', 'jpeg', 'png'],
                                                 'Please upload a JPG or PNG image.')])
    submit = SubmitField('Update Account')

    def validate_username(self, username):
        from models import User

        user = User.query.filter_by(username=username.data).first()
        if user and user.id != current_user.id:
            raise ValidationError('That username is already taken.')

    def validate_email(self, email):
        from models import User

        user = User.query.filter_by(email=email.data.lower()).first()
        if user and user.id != current_user.id:
            raise ValidationError('That email is already registered.')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Recipe or post', validators=[DataRequired(), Length(max=10000)])
    submit = SubmitField('Save Post')
