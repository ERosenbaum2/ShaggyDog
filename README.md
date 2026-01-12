# Shaggy Dog Web Application

Transform human headshots into dog versions using AI! This web application uses OpenAI's GPT-4 Vision to analyze faces and DALL-E 3 to generate beautiful transition images from human to dog.

## Features

- 🐕 **AI-Powered Breed Detection**: Automatically identifies which dog breed matches your facial features
- 🎨 **Smooth Transitions**: Generates 2 intermediate transition images between human and dog
- 🔐 **User Authentication**: Secure registration and login with encrypted passwords
- 📸 **Image Gallery**: View all your transformations in one place
- ⚡ **Multithreaded Processing**: Fast parallel image generation
- 💾 **Database Storage**: All images securely stored in PostgreSQL

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **AI Services**: OpenAI API (GPT-4 Vision, DALL-E 3)
- **Authentication**: Flask-Login with bcrypt
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Render.com

## Setup Instructions

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ShaggyDog
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```
   DATABASE_URL=sqlite:///shaggydog.db
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
   MAX_UPLOAD_SIZE=5242880
   ```

5. **Initialize the database**
   
   The database will be automatically created when you run the app for the first time.

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   
   Open your browser and navigate to `http://localhost:5000`

### Deployment on Render

1. **Push your code to GitHub**

2. **Create a new Web Service on Render**
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file

3. **Set Environment Variables in Render Dashboard**
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `SECRET_KEY`: A secure random string (or let Render generate it)
   - `MAX_UPLOAD_SIZE`: 5242880 (5MB)

4. **Create PostgreSQL Database**
   - Add a PostgreSQL database in Render
   - The `DATABASE_URL` will be automatically set from the `render.yaml` configuration

5. **Deploy**
   - Render will automatically build and deploy your application
   - The database tables will be created on first run

## Usage

1. **Register an account** or **login** if you already have one
2. **Upload a headshot** by clicking the upload area or dragging and dropping an image
3. **Wait for processing** - the app will:
   - Analyze your face
   - Detect the matching dog breed
   - Generate 2 transition images
   - Create the final dog transformation
4. **View your transformation** in the gallery with all 4 images displayed in sequence

## Project Structure

```
ShaggyDog/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── auth.py                # Authentication utilities
├── image_processor.py     # OpenAI API integration
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── render.yaml            # Render deployment config
├── templates/             # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── gallery.html
├── static/                # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── README.md
```

## API Endpoints

- `GET /` - Redirects to login or gallery
- `GET /register` - Registration page
- `POST /register` - Create new user
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `GET /logout` - Logout user
- `GET /gallery` - User's image gallery (requires login)
- `POST /upload` - Upload and process image (requires login)
- `GET /api/images/<id>/<type>` - Get image from database (requires login)
- `GET /api/generations` - Get all user's generations (requires login)

## Security Features

- Passwords are hashed using bcrypt
- Session-based authentication
- User isolation (users can only view their own images)
- File upload validation (type and size)
- SQL injection protection via SQLAlchemy ORM

## Requirements

- Python 3.8+
- OpenAI API key
- PostgreSQL (for production) or SQLite (for development)

## License

This project is for educational purposes.

## Notes

- Image generation uses OpenAI's DALL-E 3 API, which may incur costs
- Generated images are stored as base64-encoded strings in the database
- Maximum upload size is 5MB by default
- The application uses multithreading to generate transition images in parallel for faster processing
