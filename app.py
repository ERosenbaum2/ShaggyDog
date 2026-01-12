from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import base64
from io import BytesIO

from config import Config
from models import db, User, Generation, init_db
from auth import UserLogin, register_user, authenticate_user
from image_processor import (
    encode_image_to_base64, 
    detect_dog_breed, 
    generate_transition_images
)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user:
        return UserLogin(user)
    return None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page - redirects to login if not authenticated, otherwise shows upload/gallery"""
    if current_user.is_authenticated:
        return redirect(url_for('gallery'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('register.html')
        
        user, error = register_user(username, password)
        if user:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(error or 'Registration failed', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('gallery'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = authenticate_user(username, password)
        if user:
            login_user(UserLogin(user))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('gallery'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/gallery')
@login_required
def gallery():
    """Display user's generated images"""
    generations = Generation.query.filter_by(user_id=current_user.user.id)\
                                  .order_by(Generation.created_at.desc())\
                                  .all()
    return render_template('gallery.html', generations=generations)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle image upload and generation"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > Config.MAX_UPLOAD_SIZE:
        return jsonify({'error': f'File too large. Maximum size: {Config.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB'}), 400
    
    try:
        # Encode image to base64
        original_image_base64 = encode_image_to_base64(file)
        
        # Detect dog breed
        breed = detect_dog_breed(original_image_base64)
        
        # Generate transition images
        transition_1, transition_2, final_dog = generate_transition_images(
            original_image_base64, 
            breed, 
            Config.TRANSITION_COUNT
        )
        
        # Save to database
        generation = Generation(
            user_id=current_user.user.id,
            original_image=original_image_base64,
            transition_image_1=transition_1,
            transition_image_2=transition_2,
            final_dog_image=final_dog,
            detected_breed=breed
        )
        
        db.session.add(generation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'generation_id': generation.id,
            'breed': breed
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500

@app.route('/api/images/<int:generation_id>/<image_type>')
@login_required
def get_image(generation_id, image_type):
    """Serve image from database"""
    generation = Generation.query.get_or_404(generation_id)
    
    # Verify user owns this generation
    if generation.user_id != current_user.user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get the requested image
    image_map = {
        'original': generation.original_image,
        'transition1': generation.transition_image_1,
        'transition2': generation.transition_image_2,
        'final': generation.final_dog_image
    }
    
    if image_type not in image_map:
        return jsonify({'error': 'Invalid image type'}), 400
    
    image_base64 = image_map[image_type]
    image_data = base64.b64decode(image_base64)
    
    return send_file(
        BytesIO(image_data),
        mimetype='image/jpeg',
        as_attachment=False
    )

@app.route('/api/generations')
@login_required
def get_generations():
    """Get all generations for current user"""
    generations = Generation.query.filter_by(user_id=current_user.user.id)\
                                  .order_by(Generation.created_at.desc())\
                                  .all()
    
    return jsonify([{
        'id': g.id,
        'breed': g.detected_breed,
        'created_at': g.created_at.isoformat()
    } for g in generations])

# Initialize database on startup
with app.app_context():
    init_db(app)

if __name__ == '__main__':
    app.run(debug=True)
