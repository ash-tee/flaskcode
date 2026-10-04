import os
import secrets

from flask import Flask, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from extensions import db
from forms import LoginForm, PostForm, RegistrationForm, UpdateAccountForm
from PIL import Image, ImageOps, UnidentifiedImageError


app = Flask(__name__)


app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '347c38e8fec2af675f02b635a20a2efe')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
CSRFProtect(app)
db.init_app(app)
from models import User, Post

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def save_picture(file_storage):
    try:
        image = Image.open(file_storage.stream)
        if image.format not in {'JPEG', 'PNG'}:
            raise ValueError('Please upload a valid JPG or PNG image.')
        if image.width * image.height > 25_000_000:
            raise ValueError('The image dimensions are too large.')
        image.verify()
        file_storage.stream.seek(0)
        image = ImageOps.exif_transpose(Image.open(file_storage.stream))
        image.thumbnail((256, 256))
        image = image.convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError('The uploaded file is not a valid image.') from error

    filename = f'{secrets.token_hex(16)}.jpg'
    picture_directory = os.path.join(current_app.static_folder, 'profile_pics')
    os.makedirs(picture_directory, exist_ok=True)
    image.save(os.path.join(picture_directory, filename), format='JPEG', quality=90)
    return filename

@app.route('/')
@app.route('/home')
def index():
    return render_template('index.html')



@app.route('/blog')
def blog():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('blog.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('blog'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f'Account created for {form.username.data}!', 'success')
        return redirect(url_for('blog'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('blog'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if not user.password.startswith(('scrypt:', 'pbkdf2:')):
                user.set_password(form.password.data)
                db.session.commit()
            login_user(user, remember=form.remember.data)
            flash('You have been logged in!', 'success')
            return redirect(url_for('blog'))
        flash('Login unsuccessful. Check your email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('blog'))


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        old_picture = current_user.image_file
        uploaded_picture = form.picture.data
        if uploaded_picture:
            try:
                current_user.image_file = save_picture(uploaded_picture)
            except ValueError as error:
                form.picture.errors.append(str(error))
                return render_template('account.html', title='Account', form=form)

        current_user.username = form.username.data
        current_user.email = form.email.data.lower()
        db.session.commit()
        if (uploaded_picture and old_picture not in {'default.svg', 'default.jpg'}
                and os.path.basename(old_picture) == old_picture):
            old_path = os.path.join(app.static_folder, 'profile_pics', old_picture)
            if os.path.isfile(old_path):
                os.remove(old_path)
        flash('Your account has been updated.', 'success')
        return redirect(url_for('account'))
    if request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created.', 'success')
        return redirect(url_for('blog'))
    return render_template('post_form.html', title='New Post', form=form, heading='Create a post')


def get_owned_post_or_403(post_id):
    post = db.get_or_404(Post, post_id)
    if post.user_id != current_user.id:
        abort(403)
    return post


@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = get_owned_post_or_403(post_id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated.', 'success')
        return redirect(url_for('blog'))
    if request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('post_form.html', title='Update Post', form=form,
                           heading='Update post')


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = get_owned_post_or_403(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.', 'success')
    return redirect(url_for('blog'))


if __name__ == '__main__':
    app.run(debug=True)
