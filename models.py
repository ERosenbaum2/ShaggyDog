from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to images
    images = db.relationship('Image', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Image(db.Model):
    __tablename__ = 'images'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    original_image = db.Column(db.LargeBinary, nullable=False)
    transition1 = db.Column(db.LargeBinary, nullable=True)  # Allow None during generation
    transition2 = db.Column(db.LargeBinary, nullable=True)  # Allow None during generation
    final_dog = db.Column(db.LargeBinary, nullable=True)  # Allow None during generation
    breed = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='processing', nullable=False)  # processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Image {self.id} - {self.breed} - {self.status}>'
