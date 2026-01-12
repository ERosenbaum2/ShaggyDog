from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to generations
    generations = db.relationship('Generation', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Generation(db.Model):
    """Image generation model"""
    __tablename__ = 'generations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Images stored as base64-encoded strings
    original_image = db.Column(db.Text, nullable=False)
    transition_image_1 = db.Column(db.Text, nullable=False)
    transition_image_2 = db.Column(db.Text, nullable=False)
    final_dog_image = db.Column(db.Text, nullable=False)
    
    # Metadata
    detected_breed = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Generation {self.id} by User {self.user_id}>'

def init_db(app):
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
