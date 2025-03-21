import os
import requests
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class AIVoiceSystem:
    def __init__(self, output_dir: str = "audio_outputs"):
        """
        Initialize the AI Voice System with API keys and character configurations.
        
        Args:
            output_dir (str): Directory to store generated audio files
        """
        # Load API keys from environment variables or use defaults
        # Note: It's strongly recommended to use environment variables for API keys
        self.api_key_1 = os.getenv("ELEVEN_LABS_API_KEY_1")
        self.api_key_2 = os.getenv("ELEVEN_LABS_API_KEY_2")
        
        if not self.api_key_1 or not self.api_key_2:
            logger.warning("One or both ElevenLabs API keys are missing. Using default keys for development only.")
            # Only use default keys if not in production
            if not os.getenv("PRODUCTION", "False").lower() == "true":
                self.api_key_1 = self.api_key_1 or "sk_84db45e49416ed792d60bcc3ee83be8b43c9b40dcbb23ba5"
                self.api_key_2 = self.api_key_2 or "sk_c8ae6c1158f899beeba71c14c3d8743a5d5ce01c0874fa05"
            else:
                raise ValueError("API keys must be provided in production environment")
            
        # Define character voices with their supported languages
        self.characters = {
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
                "id": "gCr8TeSJgJaeaIoV4RWH",
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
        
        # Initialize the output directory
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"AIVoiceSystem initialized with output directory: {self.output_dir}")

    def get_characters_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a dictionary of character data for the UI.
        
        Returns:
            Dict[str, Dict[str, Any]]: Character data with names, descriptions, and supported languages
        """
        characters_data = {}
        for name, info in self.characters.items():
            characters_data[name] = {
                "description": info["description"],
                "languages": list(info["languages"].keys())
            }
        return characters_data

    def eleven_labs_tts(self, text: str, voice_id: str, api_key: str, language: str, 
                        output_path: str = "audio_outputs/output.mp3", 
                        retry_attempts: int = 3) -> Dict[str, Any]:
        """
        Convert text to speech using the Eleven Labs API with a specific voice and language.
        
        Args:
            text (str): The text to convert to speech
            voice_id (str): The ID of the voice to use
            api_key (str): Eleven Labs API key
            language (str): The language code (en, es, fr, de, etc.)
            output_path (str): Path to save the output audio file
            retry_attempts (int): Number of retry attempts for API calls
        
        Returns:
            Dict[str, Any]: Result of the operation with success status and file path or error
        """
        # Validate input
        if not text or not text.strip():
            return {"success": False, "error": "Text cannot be empty"}
            
        if len(text) > 5000:
            return {"success": False, "error": "Text exceeds maximum length (5000 characters)"}
            
        # API endpoint for the specific voice
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        # Headers with API key
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        # Select appropriate model based on language
        model_id = "eleven_multilingual_v2" if language != "en" else "eleven_monolingual_v1"
        
        # Request body
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        # Retry logic
        for attempt in range(retry_attempts):
            try:
                # Make the API request
                logger.info(f"Sending TTS request to ElevenLabs API for voice {voice_id}, language {language}")
                response = requests.post(url, json=data, headers=headers, timeout=30)
                
                # Check if the request was successful
                if response.status_code == 200:
                    # Save the audio content to a file
                    with open(output_path, "wb") as audio_file:
                        audio_file.write(response.content)
                    logger.info(f"Audio successfully saved to {output_path}")
                    return {"success": True, "file_path": output_path, "filename": os.path.basename(output_path)}
                
                # Handle rate limiting
                elif response.status_code == 429:
                    wait_time = min(2 ** attempt, 60)  # Exponential backoff
                    logger.warning(f"Rate limited by ElevenLabs API. Retrying in {wait_time} seconds.")
                    time.sleep(wait_time)
                    continue
                
                # Handle other errors
                else:
                    error_message = f"API Error: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    
                    # Only retry for server errors (5xx)
                    if 500 <= response.status_code < 600 and attempt < retry_attempts - 1:
                        wait_time = min(2 ** attempt, 60)
                        logger.warning(f"Server error. Retrying in {wait_time} seconds.")
                        time.sleep(wait_time)
                        continue
                    
                    return {"success": False, "error": error_message}
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out (attempt {attempt+1}/{retry_attempts})")
                if attempt < retry_attempts - 1:
                    time.sleep(2)
                    continue
                return {"success": False, "error": "Request timed out after multiple attempts"}
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {str(e)}")
                return {"success": False, "error": f"Request error: {str(e)}"}
                
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                logger.error(error_message)
                return {"success": False, "error": error_message}
                
        # If we've exhausted all retries
        return {"success": False, "error": "Failed after multiple retry attempts"}

    def generate_speech(self, text: str, character: str, language: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate speech using the selected character and language.
       
        Args:
            text (str): The text to convert to speech
            character (str): The character name to use
            language (str): The language name to use
            filename (str, optional): Custom filename for the output
        
        Returns:
            Dict[str, Any]: Result of the operation with success status and file path or error
        """
        # Validate input
        if not text or not text.strip():
            return {"success": False, "error": "Text cannot be empty"}
            
        if character not in self.characters:
            logger.error(f"Character '{character}' not found")
            return {"success": False, "error": f"Character '{character}' not found"}
        
        character_info = self.characters[character]
        
        # Get the language code from the language name
        language_code = None
        for lang_name, lang_code in character_info["languages"].items():
            if lang_name.lower() == language.lower():
                language_code = lang_code
                break
        
        if not language_code:
            logger.error(f"Language '{language}' not supported by character '{character}'")
            return {"success": False, "error": f"Language '{language}' not supported by character '{character}'"}
        
        # Determine which API key to use
        api_key = self.api_key_1 if character_info["api"] == "1" else self.api_key_2
        
        # Generate a unique filename if not provided
        if not filename:
            timestamp = int(time.time())
            filename = f"{character}_{language_code}_{timestamp}.mp3"
        
        # Ensure the filename has an extension
        if not filename.endswith('.mp3'):
            filename += '.mp3'
        
        # Create the full output path
        output_path = os.path.join(self.output_dir, filename)
        
        # Generate the speech
        result = self.eleven_labs_tts(text, character_info["id"], api_key, language_code, output_path)
        
        # Add the filename to the result
        if result["success"]:
            result["filename"] = filename
            
        return result
    
    def get_supported_languages(self, character: str) -> Dict[str, Any]:
        """
        Get the supported languages for a specific character.
        
        Args:
            character (str): The character name
            
        Returns:
            Dict[str, Any]: Result with success status and languages or error
        """
        if character not in self.characters:
            return {"success": False, "error": f"Character '{character}' not found"}
            
        languages = list(self.characters[character]["languages"].keys())
        return {"success": True, "languages": languages}
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Remove audio files older than the specified age to free up disk space.
        
        Args:
            max_age_hours (int): Maximum age of files in hours
            
        Returns:
            int: Number of files removed
        """
        try:
            # Calculate the cutoff time
            cutoff_time = time.time() - (max_age_hours * 3600)
            
            # Get all files in the output directory
            files_removed = 0
            for file_path in Path(self.output_dir).glob('*.mp3'):
                # Check if the file is older than the cutoff time
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    files_removed += 1
            
            if files_removed > 0:
                logger.info(f"Removed {files_removed} old audio files")
                
            return files_removed
        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
            return 0