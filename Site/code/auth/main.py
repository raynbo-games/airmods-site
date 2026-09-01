from flask import abort, redirect, url_for, session, current_app, Blueprint, request, render_template, jsonify
from functools import wraps
from werkzeug.exceptions import Forbidden
from Site.code.auth.database import AUTH_LEVEL, get_auth, get_user_from_id, create_user, verify_username

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.context_processor
def inject_auth_global():
    return dict(title="Auth")

def get_user():
    if not 'user-id' in session:
        return None
    user = get_user_from_id(session['user-id'])
    if user["auth"] == get_auth("BANNED"):
        abort(403, "User is banned")
    return user

def login_required():
    def decorator_login_required(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if 'user-id' not in session:
                return redirect(url_for('auth.login', next=request.full_path))
            return func(*args, **kwargs)
        return decorated_function
    return decorator_login_required

def auth_required(level: AUTH_LEVEL):
    def decorator_auth_required(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if 'user-id' not in session:
                abort(401, "No user logged in")
            if get_user()['auth'] < get_auth(level):
                abort(403, "User does not have valid auth level")
            return func(*args, **kwargs)
        return decorated_function
    return decorator_auth_required

@bp.route('/login')
def login():
    next_url = request.args.get('next') or url_for('root.home')
    return render_template('auth/login.html', next_url=next_url)

@bp.route('/login/google')
def login_google():
    google = current_app.config['GOOGLE']
    next_url = request.args.get('next') or url_for('root.home')
    redirect_uri = url_for('auth.authorize', _external=True)
    return google.authorize_redirect(redirect_uri, state=next_url)

@bp.route('/create/verify')
def verify():
    username = request.args.get('username')
    return jsonify(verify_username(username))

@bp.route('/create', methods=['GET', 'POST'])
def create():
    if 'google-user' not in session:
        return redirect(url_for('auth.login'))

    next_url = request.args.get('next') or url_for('root.home')
    user_info = session['google-user']

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        verify = verify_username(username)
        if not verify["valid"]: return f"Invalid username input: {verify["message"]}"
        create_user(user_info["sub"], user_info["email"], username)
        session['user-id'] = user_info["sub"]
        session.pop('google-user', None)
        return redirect(next_url)

    return render_template(
        'auth/create.html',
        next_url=next_url,
    )

@bp.route('/authorize')
def authorize():
    google = current_app.config['GOOGLE']
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    next_url = request.args.get('state') or url_for('root.home')

    if user_info:
        user = get_user_from_id(user_info["sub"])
        if user:
            session['user-id'] = user_info["sub"]
        else:
            session['google-user'] = user_info
            return redirect(url_for('auth.create', next=next_url))

    return redirect(next_url)

@bp.route('/logout')
def logout():
    session.pop('user-id', None)
    return redirect('/')
