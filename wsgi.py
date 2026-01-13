"""
WSGI entry point for production deployment.
Use this with gunicorn, uwsgi, or other WSGI servers.
"""
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("WSGI ENTRY POINT LOADING")
logger.info("=" * 80)
logger.info(f"PORT environment variable: {os.getenv('PORT', 'Not set')}")
logger.info(f"PYTHON_VERSION: {os.getenv('PYTHON_VERSION', 'Not set')}")

from app import app

logger.info("Flask app imported successfully")
logger.info(f"App name: {app.name}")
logger.info("=" * 80)

if __name__ == "__main__":
    logger.info("Running app directly (not via gunicorn)")
    app.run()
