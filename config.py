import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///shaggydog.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    
    # Domain configuration
    DOMAIN = os.getenv('DOMAIN', 'shaggydog.lol')
    # Don't set SERVER_NAME - Flask will auto-detect from request headers when behind a proxy
    # Setting SERVER_NAME restricts Flask to only accept requests for that hostname
    SERVER_NAME = None
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'https')
    
    # Environment
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
