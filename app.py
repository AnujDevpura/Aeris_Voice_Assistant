from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for, flash
from system import IntegratedVoiceSystem
import os
import time
import logging
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import json
import uuid
from authentication import login_user, register_user, reset_password

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 days in seconds

# Handle reverse proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Setup rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration
AUDIO_OUTPUT_DIR = os.getenv('AUDIO_OUTPUT_DIR', 'audio_outputs')
os.makedirs(AUDIO_OUTPUT_DIR, exist_ok=True)

# Get Google API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY environment variable not set")
    raise ValueError("GOOGLE_API_KEY environment variable not set")

# Initialize the integrated voice system
try:
    voice_system = IntegratedVoiceSystem(GOOGLE_API_KEY, AUDIO_OUTPUT_DIR)
    logger.info("Voice system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize voice system: {str(e)}")
    raise

# Database setup
def get_db_connection():
    conn = sqlite3.connect('voice_assistant.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Load characters data from file or use the voice system method
def load_characters():
    try:
        return voice_system.get_characters_data()
    except:
        with open('characters.json', 'r') as file:
            return json.load(file)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Ensure session has a unique ID
@app.before_request
def ensure_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

# Routes for authentication
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        result = login_user(request.form)
        if 'user_id' in result:
            session['user_id'] = result['user_id']
            session['user_name'] = result['user_name']
            
            if 'rememberMe' in request.form:
                # Set session to last longer (30 days)
                session.permanent = True
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash(result.get('message', 'Invalid email or password'), 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if 'termsCheck' not in request.form:
            flash('You must agree to the Terms & Conditions', 'error')
            return render_template('signup.html')
        
        result = register_user(request.form)
        if 'user_id' in result:
            session['user_id'] = result['user_id']
            session['user_name'] = result['user_name']
            return redirect(url_for('index'))
        else:
            flash(result.get('message', 'Registration failed'), 'error')
    
    return render_template('signup.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password_route():
    if request.method == 'POST':
        result = reset_password(request.form)
        flash(result.get('message', 'Password reset link has been sent to your email'), 
              'success' if result.get('success', False) else 'error')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Main application routes (with authentication added)
@app.route('/')
@login_required
def index():
    """Render the home page"""
    try:
        characters_data = voice_system.get_characters_data()
        return render_template('index.html', characters=characters_data)
    except Exception as e:
        logger.error(f"Error loading home page: {str(e)}")
        return jsonify({"error": "Failed to load application"}), 500

@app.route('/get_languages', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def get_languages():
    """Get supported languages for a character"""
    try:
        data = request.json
        if not data or 'character' not in data:
            return jsonify({"success": False, "error": "Character parameter required"}), 400
            
        character = data.get('character')
        
        # Get all characters data
        characters_data = voice_system.get_characters_data()
        
        # If the character data cannot be found, fallback to the hardcoded list
        if character not in characters_data:
            # Get from the hardcoded list in the /get_characters endpoint
            all_characters = {
                "Monika": {
                    "languages": {
                        "English": "en",
                        "Hindi": "hi",
                        "Arabic": "ar",
                        "Bulgarian": "bg",
                        "Czech": "cs",
                        "Portuguese": "pt",
                        "Finnish": "fi",
                        "Indonesian": "id"
                    }
                },
                "Meera": {
                    "languages": {
                        "English": "en",
                        "Tamil": "ta",
                        "Spanish": "es",
                        "Polish": "pl",
                        "German": "de",
                        "Italian": "it",
                        "French": "fr",
                        "Arabic": "ar"
                    }
                },
                "Danielle": {
                    "languages": {
                        "English": "en",
                        "Bulgarian": "bg",
                        "Czech": "cs",
                        "German": "de",
                        "Spanish": "es",
                        "Hindi": "hi",
                        "Italian": "it",
                        "French": "fr",
                        "Arabic": "ar"
                    }
                },
                "Adam": {
                    "languages": {
                        "English": "en",
                        "Hindi": "hi",
                        "Portuguese": "pt",
                        "Greek": "el",
                        "Polish": "pl",
                        "French": "fr",
                        "Indonesian": "id"
                    }
                },
                "Neeraj": {
                    "languages": {
                        "Hindi": "hi",
                        "English": "en",
                        "German": "de",
                        "Spanish": "es",
                        "Greek": "el",
                        "Russian": "ru"
                    }
                },
                "Mark": {
                    "languages": {
                        "English": "en",
                        "German": "de",
                        "Spanish": "es",
                        "Polish": "pl",
                        "Portuguese": "pt",
                        "Filipino": "tl",
                        "Italian": "it",
                        "Hindi": "hi",
                        "Czech": "cs"
                    }
                }
            }
            
            if character in all_characters:
                return jsonify({
                    "success": True,
                    "languages": all_characters[character]["languages"]
                })
            else:
                return jsonify({"success": False, "error": "Character not found"}), 404
        
        # Return the languages for the character
        return jsonify({
            "success": True,
            "languages": characters_data[character]["languages"]
        })
    except Exception as e:
        logger.error(f"Error in get_languages: {str(e)}")
        return jsonify({"success": False, "error": "Server error"}), 500

@app.route('/process_audio', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def process_audio():
    """Process audio and return a response"""
    temp_file_path = None
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file uploaded'}), 400
            
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        # Security check for file type
        if not audio_file.filename.lower().endswith(('.wav', '.mp3', '.ogg')):
            return jsonify({'success': False, 'error': 'Invalid file format'}), 400
            
        # Generate a unique filename
        timestamp = int(time.time())
        session_id = session.get('session_id', 'unknown')
        temp_file_path = f"temp_{session_id}_{timestamp}.wav"
        audio_file.save(temp_file_path)
        
        # Get parameters
        target_language = request.form.get('language', 'English')
        character = request.form.get('character', 'Monika')
        
        # Process the audio
        result = voice_system.process_audio_sync(temp_file_path, target_language, character)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in process_audio: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Clean up the temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {e}")

@app.route('/process_text', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def process_text():
    """Process text input and generate speech"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400
            
        text = data.get('text')
        source_language = data.get('source_language', 'English')
        target_language = data.get('target_language', 'English')
        character = data.get('character', 'Monika')
        
        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400
        
        # Process the text
        result = voice_system.process_text_input(text, source_language, target_language, character)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in process_text: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/generate_speech', methods=['POST'])
@login_required
@limiter.limit("20 per minute")
def generate_speech():
    """Generate speech from text without AI processing"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400
            
        text = data.get('text')
        character = data.get('character')
        language = data.get('language')
        custom_filename = data.get('filename')
        
        if not text or not character or not language:
            return jsonify({"success": False, "error": "Missing required parameters"}), 400
        
        # Validate text length to prevent abuse
        if len(text) > 2000:
            return jsonify({"success": False, "error": "Text too long (max 2000 characters)"}), 400
        
        # Generate speech
        result = voice_system.tts_system.generate_speech(text, character, language, custom_filename)
        
        if result["success"]:
            return jsonify({
                "success": True,
                "message": "Speech generated successfully",
                "audio_file": f"/audio/{result['filename']}"
            })
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error in generate_speech: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/audio/<path:filename>')
@login_required
def get_audio(filename):
    """Serve the generated audio file"""
    try:
        file_path = os.path.join(AUDIO_OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            logger.warning(f"Requested audio file not found: {filename}")
            return jsonify({"error": "Audio file not found"}), 404
            
        return send_file(file_path, mimetype="audio/mpeg")
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {str(e)}")
        return jsonify({"error": "Failed to retrieve audio file"}), 500

@app.route('/record_audio', methods=['GET'])
@login_required
def record_audio_page():
    """Render the audio recording page"""
    return render_template('record.html')

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({"status": "healthy", "timestamp": time.time()})

@app.route('/get_characters', methods=['GET'])
def get_characters():
    try:
        # Updated character data with voice IDs and language codes
        characters = {
            "Monika": {
                "id": "1qEiC6qsybMkmnNdVMbK",
                "api": "1",
                "description": "Versatile multilingual female voice with natural intonation",
                "languages": {
                    "English": "en",
                    "Hindi": "hi",
                    "Arabic": "ar",
                    "Bulgarian": "bg",
                    "Czech": "cs",
                    "Portuguese": "pt",
                    "Finnish": "fi",
                    "Indonesian": "id"
                }
            },
            "Meera": {
                "id": "1qEiC6qsybMkmnNdVMbK",
                "api": "1",
                "description": "Expressive female voice with diverse language capabilities",
                "languages": {
                    "English": "en",
                    "Tamil": "ta",
                    "Spanish": "es",
                    "Polish": "pl",
                    "German": "de",
                    "Italian": "it",
                    "French": "fr",
                    "Arabic": "ar"
                }
            },
            "Danielle": {
                "id": "FVQMzxJGPUBtfz1Azdoy",
                "api": "1",
                "description": "Clear and professional female voice with European language support",
                "languages": {
                    "English": "en",
                    "Bulgarian": "bg",
                    "Czech": "cs",
                    "German": "de",
                    "Spanish": "es",
                    "Hindi": "hi",
                    "Italian": "it",
                    "French": "fr",
                    "Arabic": "ar"
                }
            },
            "Adam": {
                "id": "NFG5qt843uXKj4pFvR7C",
                "api": "2",
                "description": "A middle aged 'Brit' with a velvety laid back, late night talk show host timbre",
                "languages": {
                    "English": "en",
                    "Hindi": "hi",
                    "Portuguese": "pt",
                    "Greek": "el",
                    "Polish": "pl",
                    "French": "fr",
                    "Indonesian": "id"
                }
            },
            "Neeraj": {
                "id": "zgqefOY5FPQ3bB7OZTVR",
                "api": "2",
                "description": "Veteran Indian actor voice, great for narrative work and documentaries",
                "languages": {
                    "Hindi": "hi",
                    "English": "en",
                    "German": "de",
                    "Spanish": "es",
                    "Greek": "el",
                    "Russian": "ru"
                }
            },
            "Mark": {
                "id": "UgBBYS2sOqTuMpoF3BR0",
                "api": "2",
                "description": "Casual, young-adult male voice speaking naturally, perfect for conversational AI",
                "languages": {
                    "English": "en",
                    "German": "de",
                    "Spanish": "es",
                    "Polish": "pl",
                    "Portuguese": "pt",
                    "Filipino": "tl",
                    "Italian": "it",
                    "Hindi": "hi",
                    "Czech": "cs"
                }
            }
        }
        
        return jsonify({
            "success": True,
            "characters": characters
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# Map older API endpoints to new ones for backwards compatibility
@app.route('/api/speech-to-text', methods=['POST'])
@login_required
def speech_to_text():
    """Legacy endpoint for speech-to-text"""
    return process_audio()

@app.route('/api/text-to-speech', methods=['POST'])
@login_required
def text_to_speech():
    """Legacy endpoint for text-to-speech"""
    return generate_speech()

@app.route('/api/process-message', methods=['POST'])
@login_required
def process_message():
    """Legacy endpoint for processing messages"""
    return process_text()

if __name__ == '__main__':
    # Get configuration from environment variables
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting application on port {port}, debug mode: {debug_mode}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)