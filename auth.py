import bcrypt
from flask_login import UserMixin
from models import User, db

class UserLogin(UserMixin):
    """Wrapper for Flask-Login user session"""
    def __init__(self, user):
        self.user = user
    
    def get_id(self):
        return str(self.user.id)

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def register_user(username, password):
    """Register a new user"""
    # Check if username already exists
    if User.query.filter_by(username=username).first():
        return None, "Username already exists"
    
    # Create new user
    password_hash = hash_password(password)
    user = User(username=username, password_hash=password_hash)
    
    try:
        db.session.add(user)
        db.session.commit()
        return user, None
    except Exception as e:
        db.session.rollback()
        return None, f"Error creating user: {str(e)}"

def authenticate_user(username, password):
    """Authenticate a user and return User object if successful"""
    user = User.query.filter_by(username=username).first()
    
    if user and verify_password(password, user.password_hash):
        return user
    return None
