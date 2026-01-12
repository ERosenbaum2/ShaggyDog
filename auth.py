import bcrypt
from functools import wraps
from flask import session, redirect, url_for, flash
from models import User, db

def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def register_user(username, password):
    """Register a new user."""
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return None, "Username already exists"
    
    # Hash password and create user
    password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash)
    
    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except Exception as e:
        db.session.rollback()
        return None, f"Error creating user: {str(e)}"

def verify_user(username, password):
    """Verify user credentials."""
    user = User.query.filter_by(username=username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current logged-in user."""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None
