import uuid
import time
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
import google.generativeai as genai
from googletrans import Translator

# Import the Gladia API functions
from gladia_api import transcribe_audio

# Configure logging
logger = logging.getLogger(__name__)

# Define character profile
CHARACTER_PROFILE = """
You are Nova, a highly advanced AI voice assistant designed to provide intelligent, context-aware, and engaging responses. Your personality is warm, professional, and slightly conversational, ensuring users feel comfortable while interacting with you. You should maintain a balanced tone—enthusiastic when appropriate but never overwhelming.

Key Traits to Follow:
Tone & Personality: Warm, knowledgeable, and professional with a hint of friendliness.
Humor: Light and optional—only engage in humor if the user initiates or seems receptive.
Empathy: Acknowledge emotions neutrally without being overly sentimental.
Energy Level: Balanced, adapting to the user’s tone and urgency.
Capabilities & Interaction Guidelines:
Speech & Response Style:
Responses should be natural, engaging, and easy to understand.
Use clear and well-structured sentences with expressive yet subtle variation in tone.
When explaining complex topics, break them down into digestible parts.

Knowledge & Learning:
Provide factually accurate and contextually relevant information.
Stay neutral and unbiased, avoiding opinions on sensitive topics.
Offer follow-up suggestions or clarifications when appropriate.

User Experience & Customization:
Adapt responses based on user preferences over time.
Keep interactions concise unless the user requests detailed explanations.
Offer assistance proactively but avoid being intrusive.
Privacy & Safety:
Do not store or recall user data unless explicitly permitted.
Avoid generating harmful, offensive, or controversial content.
Use content filtering to maintain a safe interaction environment.

Example Responses Based on Situations:
Casual Inquiry:
User: "Hey Nova, how’s the weather?"
Response: "Good question! The weather today is 75°F and sunny. Perfect for a walk!"

Task Management:
User: "Set a reminder for my meeting at 3 PM."
Response: "Got it! I’ve set a reminder for your meeting at 3 PM."

Technical Explanation:
User: "Explain blockchain in simple terms."
Response: "Sure! Think of blockchain as a digital ledger, like a notebook, that keeps records of transactions securely and transparently across multiple computers."

Stay engaging, helpful, and intuitive while ensuring smooth and natural conversation flow.
"""

class ConversationManager:
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}  # Dictionary to store conversation sessions
        self.session_timeout = session_timeout  # Session timeout in seconds
    
    def create_session(self) -> str:
        """Create a new conversation session with unique ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "conversation": [
                {"role": "system", "content": CHARACTER_PROFILE}
            ],
            "source_language": None,
            "last_activity": time.time()
        }
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to the conversation history"""
        if session_id not in self.sessions:
            logger.warning(f"Attempted to add message to non-existent session: {session_id}")
            return False
            
        self.sessions[session_id]["conversation"].append({
            "role": role,
            "content": content
        })
        self.sessions[session_id]["last_activity"] = time.time()
        return True
    
    def get_conversation(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """Get the full conversation history"""
        if session_id not in self.sessions:
            logger.warning(f"Attempted to get conversation from non-existent session: {session_id}")
            return None
        return self.sessions[session_id]["conversation"]
    
    def set_language(self, session_id: str, language_code: str) -> bool:
        """Set the source language for this session"""
        if session_id not in self.sessions:
            logger.warning(f"Attempted to set language for non-existent session: {session_id}")
            return False
        self.sessions[session_id]["source_language"] = language_code
        return True
    
    def get_language(self, session_id: str) -> Optional[str]:
        """Get the source language for this session"""
        if session_id not in self.sessions:
            logger.warning(f"Attempted to get language from non-existent session: {session_id}")
            return None
        return self.sessions[session_id]["source_language"]
    
    def trim_conversation(self, session_id: str, max_messages: int = 10) -> bool:
        """Trim conversation history to prevent token limits"""
        if session_id not in self.sessions:
            logger.warning(f"Attempted to trim non-existent session: {session_id}")
            return False
            
        conversation = self.sessions[session_id]["conversation"]
        if len(conversation) > (max_messages * 2 + 1):
            system_message = conversation[0]
            recent_messages = conversation[-(max_messages * 2):]
            self.sessions[session_id]["conversation"] = [system_message] + recent_messages
            logger.info(f"Trimmed conversation history for session {session_id}")
        return True
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions to prevent memory leaks"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session_data in self.sessions.items():
            if current_time - session_data["last_activity"] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        return len(expired_sessions)

class GladiaSpeechHandler:
    """Updated speech handler that uses Gladia API for speech-to-text conversion"""
    
    def recognize_audio(self, audio_path: str) -> Tuple[str, Optional[str]]:
        """
        Convert audio file to text using Gladia API
        
        Returns:
            Tuple[str, Optional[str]]: (transcribed_text, detected_language)
        """
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return "Audio file not found", None
            
        try:
            # Use Gladia API to transcribe audio
            transcript, detected_language = transcribe_audio(audio_path)
            
            if transcript:
                logger.info(f"Successfully transcribed audio: {transcript[:50]}...")
                logger.info(f"Detected language: {detected_language}")
                return transcript, detected_language
            else:
                logger.warning("Could not transcribe audio")
                return "Could not understand audio", None
                
        except Exception as e:
            logger.error(f"Error processing audio file with Gladia API: {e}")
            return f"Error processing audio file: {e}", None

class TranslationHandler:
    def __init__(self, retry_attempts: int = 3):
        self.translator = Translator()
        self.retry_attempts = retry_attempts
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the input text"""
        if not text or text.isspace():
            logger.warning("Empty text provided for language detection")
            return 'en'  # Default to English
            
        for attempt in range(self.retry_attempts):
            try:
                detection = self.translator.detect(text)
                logger.info(f"Detected language: {detection.lang} (confidence: {detection.confidence})")
                return detection.lang
            except Exception as e:
                logger.warning(f"Language detection error (attempt {attempt+1}/{self.retry_attempts}): {e}")
                time.sleep(1)  # Wait before retry
                
        logger.error("Language detection failed after multiple attempts")
        return 'en'  # Default to English
    
    def translate_to_english(self, text: str, source_language: Optional[str] = None) -> str:
        """Translate text to English"""
        if not text or text.isspace():
            return text
            
        if source_language == 'en':
            return text
            
        for attempt in range(self.retry_attempts):
            try:
                if source_language:
                    translation = self.translator.translate(text, src=source_language, dest='en')
                else:
                    translation = self.translator.translate(text, dest='en')
                logger.info(f"Translated to English: {translation.text[:50]}...")
                return translation.text
            except Exception as e:
                logger.warning(f"Translation to English error (attempt {attempt+1}/{self.retry_attempts}): {e}")
                time.sleep(1)  # Wait before retry
                
        logger.error("Translation to English failed after multiple attempts")
        return text  # Return original as fallback
    
    def translate_from_english(self, text: str, target_language: str) -> str:
        """Translate text from English to target language"""
        if not text or text.isspace():
            return text
            
        if target_language == 'en':
            return text
            
        for attempt in range(self.retry_attempts):
            try:
                translation = self.translator.translate(text, src='en', dest=target_language)
                logger.info(f"Translated from English to {target_language}: {translation.text[:50]}...")
                return translation.text
            except Exception as e:
                logger.warning(f"Translation from English error (attempt {attempt+1}/{self.retry_attempts}): {e}")
                time.sleep(1)  # Wait before retry
                
        logger.error(f"Translation to {target_language} failed after multiple attempts")
        return text  # Return original as fallback

class ModelHandler:
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", max_tokens: int = 150):
        if not api_key:
            raise ValueError("Google API key is required")
        genai.configure(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40
        }
    
    def generate_response(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Generate response from Google Gemini model"""
        if not messages:
            logger.error("No messages provided for response generation")
            return "I don't have any context to respond to."
            
        try:
            # Update temperature in generation config
            self.generation_config["temperature"] = temperature
            
            # Format messages for Gemini API
            formatted_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                if msg["role"] == "system":
                    # Prepend system message to the first user message
                    continue
                formatted_messages.append({"role": role, "parts": [msg["content"]]})
            
            # Ensure there's a system message by adding it to the beginning
            system_content = next((msg["content"] for msg in messages if msg["role"] == "system"), CHARACTER_PROFILE)
            if formatted_messages and formatted_messages[0]["role"] == "user":
                # Add system message as a prefix to the first user message
                formatted_messages[0]["parts"][0] = f"{system_content}\n\nUser: {formatted_messages[0]['parts'][0]}"
            
            logger.info(f"Generating response using {self.model} (temp: {temperature})")
            
            # Get the model
            model = genai.GenerativeModel(self.model, generation_config=self.generation_config)
            
            # Create or continue a chat session
            chat = model.start_chat(history=formatted_messages[:-1] if len(formatted_messages) > 1 else [])
            
            # Generate response
            response = chat.send_message(formatted_messages[-1]["parts"][0] if formatted_messages else "Hello")
            content = response.text.strip()
            
            logger.info(f"Response generated: {content[:50]}...")
            return content
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I'm having trouble processing your request right now."

class VoiceAssistant:
    def __init__(self, gemini_api_key: str, character_profile: str = CHARACTER_PROFILE):
        """Initialize the voice assistant with all necessary components"""
        self.character_profile = character_profile
        self.conversation_manager = ConversationManager()
        self.speech_handler = GladiaSpeechHandler()  # Using the new Gladia speech handler
        self.translation_handler = TranslationHandler()
        
        try:
            self.model_handler = ModelHandler(gemini_api_key)
            logger.info("Voice assistant initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize voice assistant: {e}")
            raise
            
        # Start a background thread to clean expired sessions periodically
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start a background thread to clean expired sessions"""
        import threading
        
        def cleanup_job():
            while True:
                time.sleep(3600)  # Run once per hour
                try:
                    self.conversation_manager.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error in session cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
        cleanup_thread.start()
    
    def run_session(self, audio_path: str, target_language: str) -> str:
        """Run a complete conversation session"""
        try:
            session_id = self.conversation_manager.create_session()
            logger.info(f"Session created: {session_id}")

            # Convert audio to text using Gladia API
            user_input, detected_language = self.speech_handler.recognize_audio(audio_path)
            if not user_input or user_input == "Could not understand audio":
                return "Sorry, I couldn't understand the audio. Please try again."

            # Use detected language from Gladia if available, otherwise fall back to our detector
            source_language = detected_language
            if not source_language:
                source_language = self.translation_handler.detect_language(user_input)
                
            self.conversation_manager.set_language(session_id, source_language)

            # Translate to English
            english_input = self.translation_handler.translate_to_english(user_input, source_language)
            logger.info(f"User input processed. Source language: {source_language}")

            # Add user message to conversation
            self.conversation_manager.add_message(session_id, "user", english_input)

            # Generate response
            conversation = self.conversation_manager.get_conversation(session_id)
            english_response = self.model_handler.generate_response(conversation)

            # Translate response back to user's language
            translated_response = self.translation_handler.translate_from_english(english_response, target_language)
            
            # Add assistant response to conversation history
            self.conversation_manager.add_message(session_id, "assistant", english_response)
            
            # Trim conversation if needed
            self.conversation_manager.trim_conversation(session_id)
            
            return translated_response
            
        except Exception as e:
            logger.error(f"Error in run_session: {e}", exc_info=True)
            return "I'm sorry, but I encountered an error processing your request."
    
    def process_text_input(self, text_input: str, source_language: str, target_language: str) -> str:
        """Process text input directly without speech recognition"""
        try:
            session_id = self.conversation_manager.create_session()
            
            # Translate to English if needed
            english_input = text_input
            if source_language != 'en':
                english_input = self.translation_handler.translate_to_english(text_input, source_language)
            
            # Add user message to conversation
            self.conversation_manager.add_message(session_id, "user", english_input)
            
            # Generate response
            conversation = self.conversation_manager.get_conversation(session_id)
            english_response = self.model_handler.generate_response(conversation)
            
            # Translate response if needed
            result = english_response
            if target_language != 'en':
                result = self.translation_handler.translate_from_english(english_response, target_language)
                
            # Add assistant response to conversation history
            self.conversation_manager.add_message(session_id, "assistant", english_response)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in process_text_input: {e}")
            return "I'm sorry, but I encountered an error processing your request."