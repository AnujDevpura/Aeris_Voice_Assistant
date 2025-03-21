import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import os
from datetime import datetime
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("auth.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables for email configuration
load_dotenv()
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@yourdomain.com')
RESET_LINK_BASE = os.getenv('RESET_LINK_BASE', 'http://localhost:5000/complete_reset/')

# Database connection
def get_db_connection():
    conn = sqlite3.connect('voice_assistant.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_user(form_data):
    """
    Authenticate a user and return user information if successful
    
    Args:
        form_data: Form data from request containing 'email' and 'password'
        
    Returns:
        dict: User information if login successful, error message otherwise
    """
    try:
        email = form_data.get('email', '')
        password = form_data.get('password', '')
        
        # Basic validation
        if not email or not password:
            logger.warning(f"Login attempt with missing credentials: {email}")
            return {"success": False, "message": "Email and password are required"}
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            logger.info(f"Successful login for user: {email}")
            return {
                "success": True,
                "user_id": user['id'],
                "user_name": f"{user['first_name']} {user['last_name']}",
                "message": "Login successful"
            }
        else:
            logger.warning(f"Failed login attempt for user: {email}")
            return {"success": False, "message": "Invalid email or password"}
    
    except Exception as e:
        logger.error(f"Error during login process: {str(e)}")
        return {"success": False, "message": "An error occurred during login"}

def register_user(form_data):
    """
    Register a new user
    
    Args:
        form_data: Form data from request containing user registration info
        
    Returns:
        dict: User information if registration successful, error message otherwise
    """
    try:
        first_name = form_data.get('firstName', '')
        last_name = form_data.get('lastName', '')
        email = form_data.get('email', '')
        password = form_data.get('password', '')
        
        # Basic validation
        if not first_name or not last_name or not email or not password:
            return {"success": False, "message": "All fields are required"}
        
        if len(password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters long"}
        
        # Check if email already exists
        conn = get_db_connection()
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if existing_user:
            conn.close()
            logger.warning(f"Registration attempt with existing email: {email}")
            return {"success": False, "message": "Email already exists"}
        
        # Hash password and insert new user
        hashed_password = generate_password_hash(password)
        
        conn.execute(
            'INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)',
            (first_name, last_name, email, hashed_password)
        )
        conn.commit()
        
        # Get the user ID for the new user
        user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user:
            logger.info(f"New user registered: {email}")
            return {
                "success": True,
                "user_id": user['id'],
                "user_name": f"{first_name} {last_name}",
                "message": "Registration successful"
            }
        else:
            logger.error(f"Failed to retrieve user after registration: {email}")
            return {"success": False, "message": "Registration failed"}
    
    except sqlite3.IntegrityError:
        logger.warning(f"Registration failed - integrity error for email: {email}")
        return {"success": False, "message": "Email already exists"}
    
    except Exception as e:
        logger.error(f"Error during registration process: {str(e)}")
        return {"success": False, "message": "An error occurred during registration"}

def reset_password(form_data):
    """
    Process password reset request
    
    Args:
        form_data: Form data from request containing 'email'
        
    Returns:
        dict: Success status and message
    """
    try:
        email = form_data.get('email', '')
        
        if not email:
            return {"success": False, "message": "Email is required"}
        
        # Check if user exists
        conn = get_db_connection()
        user = conn.execute('SELECT id, first_name FROM users WHERE email = ?', (email,)).fetchone()
        
        # Always return success to prevent email enumeration
        if not user:
            logger.info(f"Password reset requested for non-existent email: {email}")
            return {"success": True, "message": "If your email is registered, you will receive a password reset link"}
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expiry = datetime.now().timestamp() + 3600  # 1 hour from now
        
        # Store token in the database (create a password_resets table if it doesn't exist)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Delete any existing tokens for this user
        conn.execute('DELETE FROM password_resets WHERE user_id = ?', (user['id'],))
        
        # Insert new token
        conn.execute(
            'INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)',
            (user['id'], reset_token, expiry)
        )
        conn.commit()
        conn.close()
        
        # Send email with reset link
        reset_link = f"{RESET_LINK_BASE}{reset_token}"
        send_password_reset_email(email, user['first_name'], reset_link)
        
        logger.info(f"Password reset link sent to: {email}")
        return {"success": True, "message": "If your email is registered, you will receive a password reset link"}
    
    except Exception as e:
        logger.error(f"Error during password reset process: {str(e)}")
        return {"success": False, "message": "An error occurred while processing your request"}

def send_password_reset_email(to_email, first_name, reset_link):
    """
    Send password reset email with reset link
    
    Args:
        to_email: Recipient email address
        first_name: User's first name
        reset_link: Password reset link
    """
    try:
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            logger.warning("Email credentials not configured, skipping password reset email")
            return
        
        subject = "Reset Your Password"
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Email body
        body = f"""
        <html>
            <body>
                <h2>Password Reset</h2>
                <p>Hello {first_name},</p>
                <p>We received a request to reset your password. Click the link below to reset your password:</p>
                <p><a href="{reset_link}">Reset Password</a></p>
                <p>If you didn't request this, you can safely ignore this email.</p>
                <p>The link will expire in 1 hour.</p>
                <p>Best regards,<br>Voice Assistant Team</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to email server and send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Password reset email sent to: {to_email}")
    
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        # We don't raise the exception to prevent the API from failing if email sending fails

# Additional function for completing password reset (not directly used in app.py but needed for full functionality)
def complete_password_reset(token, new_password):
    """
    Complete the password reset process by setting a new password
    
    Args:
        token: Reset token from email
        new_password: New password to set
        
    Returns:
        dict: Success status and message
    """
    try:
        if not token or not new_password:
            return {"success": False, "message": "Token and new password are required"}
        
        if len(new_password) < 8:
            return {"success": False, "message": "Password must be at least 8 characters long"}
        
        conn = get_db_connection()
        
        # Get the reset record
        now = datetime.now().timestamp()
        reset = conn.execute(
            'SELECT user_id, expires_at FROM password_resets WHERE token = ?',
            (token,)
        ).fetchone()
        
        if not reset:
            conn.close()
            return {"success": False, "message": "Invalid or expired token"}
        
        if reset['expires_at'] < now:
            # Token expired, delete it
            conn.execute('DELETE FROM password_resets WHERE token = ?', (token,))
            conn.commit()
            conn.close()
            return {"success": False, "message": "Reset token has expired"}
        
        # Update the user's password
        user_id = reset['user_id']
        hashed_password = generate_password_hash(new_password)
        
        conn.execute(
            'UPDATE users SET password = ? WHERE id = ?',
            (hashed_password, user_id)
        )
        
        # Delete the used token
        conn.execute('DELETE FROM password_resets WHERE token = ?', (token,))
        conn.commit()
        
        # Get user info for return
        user = conn.execute('SELECT first_name, last_name FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        
        logger.info(f"Password reset completed for user ID: {user_id}")
        return {
            "success": True,
            "message": "Your password has been updated successfully",
            "user_id": user_id,
            "user_name": f"{user['first_name']} {user['last_name']}" if user else ""
        }
    
    except Exception as e:
        logger.error(f"Error during password reset completion: {str(e)}")
        return {"success": False, "message": "An error occurred while resetting your password"}