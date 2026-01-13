from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from config import Config
from models import db, User, Image
from auth import register_user, verify_user, login_required, get_current_user
from openai_service import detect_breed, generate_transition_image, generate_final_dog_image
import os
import logging
import threading
from io import BytesIO
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Log configuration on startup
logger.info("=" * 80)
logger.info("APPLICATION STARTING")
logger.info("=" * 80)
logger.info(f"Flask app name: {app.name}")
logger.info(f"Debug mode: {app.config.get('DEBUG')}")
logger.info(f"Server name: {app.config.get('SERVER_NAME')}")
logger.info(f"Preferred URL scheme: {app.config.get('PREFERRED_URL_SCHEME')}")
logger.info(f"Domain: {app.config.get('DOMAIN')}")
logger.info(f"Upload folder: {app.config.get('UPLOAD_FOLDER')}")
logger.info(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
logger.info("=" * 80)

# Set preferred URL scheme for URL generation (for HTTPS in production)
# This helps Flask generate correct URLs when behind a reverse proxy
if app.config.get('PREFERRED_URL_SCHEME') == 'https':
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database
db.init_app(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created/verified")

# Add request logging middleware
@app.before_request
def log_request_info():
    """Log all incoming requests."""
    logger.info("=" * 80)
    logger.info(f"INCOMING REQUEST")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Path: {request.path}")
    logger.info(f"Host: {request.host}")
    logger.info(f"Remote address: {request.remote_addr}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Session: {dict(session)}")
    logger.info("=" * 80)

@app.after_request
def log_response_info(response):
    """Log all outgoing responses."""
    logger.info(f"OUTGOING RESPONSE: Status {response.status_code}, Headers: {dict(response.headers)}")
    return response

@app.route('/')
def index():
    """Home page - redirect to login or gallery."""
    logger.info("INDEX route called")
    logger.info(f"Session user_id: {session.get('user_id', 'None')}")
    if 'user_id' in session:
        logger.info("User is logged in, redirecting to gallery")
        return redirect(url_for('gallery'))
    logger.info("User is not logged in, redirecting to login")
    return redirect(url_for('login'))

@app.route('/favicon.ico')
@app.route('/favicon.png')
def favicon():
    """Handle favicon requests to prevent 404 errors."""
    return '', 204  # No content

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
        
        # Register user
        user, error = register_user(username, password)
        if error:
            flash(error, 'error')
            return render_template('register.html')
        
        # Auto-login after registration
        session['user_id'] = user.id
        session['username'] = user.username
        flash('Registration successful! Welcome!', 'success')
        return redirect(url_for('gallery'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    logger.info(f"LOGIN route called with method: {request.method}")
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')
        
        user = verify_user(username, password)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('gallery'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET'])
@login_required
def upload_page():
    """Image upload page."""
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Process image upload and generate transformations."""
    logger.info("UPLOAD route called (POST)")
    logger.info(f"Request files: {list(request.files.keys())}")
    
    if 'image' not in request.files:
        logger.warning("No image file in request")
        flash('No image file provided.', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['image']
    if file.filename == '':
        logger.warning("Empty filename in image upload")
        flash('No image file selected.', 'error')
        return redirect(url_for('upload_page'))
    
    logger.info(f"Processing image upload: {file.filename}")
    
    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'jfif', 'bmp', 'tiff', 'tif', 'ico', 'svg'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        logger.warning(f"Invalid file type: {file.filename}")
        flash('Invalid file type. Please upload an image (PNG, JPG, JPEG, GIF, WEBP, JFIF, BMP, TIFF, ICO, or SVG).', 'error')
        return redirect(url_for('upload_page'))
    
    try:
        # Read image data
        logger.info("Reading image data")
        image_data = file.read()
        logger.info(f"Image data size: {len(image_data)} bytes")
        
        # Detect breed
        logger.info("Starting breed detection")
        file.seek(0)  # Reset file pointer
        breed, reasoning = detect_breed(file)
        logger.info(f"Breed detection result: breed={breed}, reasoning={reasoning[:100] if reasoning else 'None'}")
        
        if not breed:
            logger.error(f"Breed detection failed: {reasoning}")
            flash(f'Error detecting breed: {reasoning}', 'error')
            return redirect(url_for('upload_page'))
        
        # Save image record immediately with processing status
        user_id = session['user_id']
        image_record = Image(
            user_id=user_id,
            original_image=image_data,
            breed=breed,
            status='processing'
        )
        
        db.session.add(image_record)
        db.session.commit()
        image_id = image_record.id
        
        logger.info(f"Created image record {image_id} with status 'processing'")
        
        # Start background thread to generate images
        def generate_images_background(image_id, image_data, breed):
            """Generate images in background thread."""
            with app.app_context():
                try:
                    logger.info(f"Background thread: Starting image generation for image {image_id}")
                    
                    # Generate transition images
                    logger.info(f"Background: Generating transition image 1 for image {image_id}")
                    transition1_data = generate_transition_image(image_data, breed, 1)
                    logger.info(f"Background: Transition image 1 {'completed' if transition1_data else 'failed'} for image {image_id}")
                    
                    logger.info(f"Background: Generating transition image 2 for image {image_id}")
                    transition2_data = generate_transition_image(image_data, breed, 2)
                    logger.info(f"Background: Transition image 2 {'completed' if transition2_data else 'failed'} for image {image_id}")
                    
                    logger.info(f"Background: Generating final dog image for image {image_id}")
                    final_dog_data = generate_final_dog_image(image_data, breed)
                    logger.info(f"Background: Final dog image {'completed' if final_dog_data else 'failed'} for image {image_id}")
                    
                    # Update database
                    image_record = Image.query.get(image_id)
                    if image_record and all([transition1_data, transition2_data, final_dog_data]):
                        image_record.transition1 = transition1_data
                        image_record.transition2 = transition2_data
                        image_record.final_dog = final_dog_data
                        image_record.status = 'completed'
                        db.session.commit()
                        logger.info(f"Background: Successfully completed image generation for image {image_id}")
                    else:
                        if image_record:
                            image_record.status = 'failed'
                            db.session.commit()
                        logger.error(f"Background: Failed to generate all images for image {image_id}")
                        
                except Exception as e:
                    logger.error(f"Background: Exception in image generation for image {image_id}: {type(e).__name__}: {str(e)}", exc_info=True)
                    try:
                        image_record = Image.query.get(image_id)
                        if image_record:
                            image_record.status = 'failed'
                            db.session.commit()
                    except:
                        pass
        
        # Start background thread
        thread = threading.Thread(target=generate_images_background, args=(image_id, image_data, breed))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started background thread for image {image_id}, returning response to user")
        flash('Image uploaded! Generating transformations in the background. Check your gallery in a minute.', 'info')
        return redirect(url_for('gallery'))
        
    except Exception as e:
        logger.error(f"EXCEPTION in upload route: {type(e).__name__}: {str(e)}", exc_info=True)
        db.session.rollback()
        flash(f'Error processing image: {str(e)}', 'error')
        return redirect(url_for('upload_page'))

@app.route('/gallery')
@login_required
def gallery():
    """User's image gallery."""
    logger.info("GALLERY route called")
    user_id = session['user_id']
    images = Image.query.filter_by(user_id=user_id).order_by(Image.created_at.desc()).all()
    logger.info(f"Found {len(images)} images for user {user_id}")
    return render_template('gallery.html', images=images)

@app.route('/image/<int:image_id>/<image_type>')
@login_required
def serve_image(image_id, image_type):
    """Serve an image from the database (user-specific)."""
    user_id = session['user_id']
    image_record = Image.query.filter_by(id=image_id, user_id=user_id).first_or_404()
    
    # Determine which image to serve
    image_data = None
    mimetype = 'image/jpeg'
    
    if image_type == 'original':
        image_data = image_record.original_image
    elif image_type == 'transition1':
        image_data = image_record.transition1
    elif image_type == 'transition2':
        image_data = image_record.transition2
    elif image_type == 'final':
        image_data = image_record.final_dog
    else:
        flash('Invalid image type.', 'error')
        return redirect(url_for('gallery'))
    
    # If image is still processing, return 204 No Content
    if image_data is None:
        return '', 204
    
    return send_file(
        BytesIO(image_data),
        mimetype=mimetype,
        as_attachment=False
    )

# Add error handler for logging
@app.errorhandler(Exception)
def handle_exception(e):
    """Log all exceptions."""
    logger.error(f"EXCEPTION OCCURRED: {type(e).__name__}: {str(e)}", exc_info=True)
    raise  # Re-raise to let Flask handle it

if __name__ == '__main__':
    # Configure for production or development
    debug_mode = app.config.get('DEBUG', False)
    port = int(os.getenv('PORT', 5000))
    
    logger.info(f"Starting Flask app in {'DEBUG' if debug_mode else 'PRODUCTION'} mode on port {port}")
    
    # If SERVER_NAME is set, use it (for production with domain)
    if app.config.get('SERVER_NAME'):
        logger.info(f"Using SERVER_NAME: {app.config.get('SERVER_NAME')}")
        app.run(debug=debug_mode, host='0.0.0.0', port=port)
    else:
        # Development mode - localhost
        logger.info("No SERVER_NAME set, using default host")
        app.run(debug=debug_mode, host='0.0.0.0', port=port)
