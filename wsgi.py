"""
WSGI entry point for production deployment.
Use this with gunicorn, uwsgi, or other WSGI servers.
"""
from app import app

if __name__ == "__main__":
    app.run()
