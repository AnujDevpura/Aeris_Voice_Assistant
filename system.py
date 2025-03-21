import os
import logging
from typing import Dict, Any, Optional, List
from assistant import VoiceAssistant
from tts import AIVoiceSystem
import time
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("system.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class IntegratedVoiceSystem:
    """
    Integrated system that combines the voice assistant and TTS components.
    This class provides high-level methods for the Flask application to use.
    """
    def __init__(self, gemini_api_key: str, audio_output_dir: str = "audio_outputs"):
        """
        Initialize the integrated voice system.
        
        Args:
            gemini_api_key (str): Gemini API key
            audio_output_dir (str): Directory to store audio outputs
        """
        self.output_dir = audio_output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize components
        self.voice_assistant = VoiceAssistant(gemini_api_key)
        self.tts_system = AIVoiceSystem(output_dir=audio_output_dir)
        
        # Start background task for cleanup
        self._start_cleanup_task()
        
        # Set up processing queue for background tasks
        self.task_queue = queue.Queue()
        self._start_worker_thread()
        
        logger.info("Integrated Voice System initialized successfully")
    
    def _start_cleanup_task(self):
        """Start a background task to clean up old files"""
        def cleanup_job():
            while True:
                try:
                    # Run cleanup every 6 hours
                    time.sleep(6 * 3600)
                    self.tts_system.cleanup_old_files(max_age_hours=24)
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
        
        thread = threading.Thread(target=cleanup_job, daemon=True)
        thread.start()
    
    def _start_worker_thread(self):
        """Start a worker thread to process tasks in the background"""
        def worker():
            while True:
                try:
                    # Get a task from the queue
                    task, args, kwargs, result_queue = self.task_queue.get()
                    
                    # Execute the task
                    result = task(*args, **kwargs)
                    
                    # Put the result in the result queue
                    if result_queue:
                        result_queue.put(result)
                    
                    # Mark the task as done
                    self.task_queue.task_done()
                except Exception as e:
                    logger.error(f"Error in worker thread: {str(e)}")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def process_audio_sync(self, audio_path: str, target_language: str, character: str) -> Dict[str, Any]:
        """
        Process audio synchronously and return the result.
        
        Args:
            audio_path (str): Path to the audio file
            target_language (str): Target language for the response
            character (str): Character to use for TTS
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # Process the audio file using the voice assistant
            response_text = self.voice_assistant.run_session(audio_path, target_language)
            
            # Generate speech from the response
            timestamp = int(time.time())
            filename = f"{character}_{target_language}_{timestamp}.mp3"
            
            # Convert response to speech
            result = self.tts_system.generate_speech(response_text, character, target_language, filename)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Audio processed successfully",
                    "response_text": response_text,
                    "audio_file": f"/audio/{result['filename']}"
                }
            else:
                logger.error(f"TTS generation failed: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get('error', "TTS generation failed")
                }
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_audio_async(self, audio_path: str, target_language: str, character: str) -> str:
        """
        Process audio asynchronously and return a task ID.
        
        Args:
            audio_path (str): Path to the audio file
            target_language (str): Target language for the response
            character (str): Character to use for TTS
            
        Returns:
            str: Task ID
        """
        # Generate a unique task ID
        task_id = f"task_{int(time.time())}_{hash(audio_path) % 10000}"
        
        # Put the task in the queue
        self.task_queue.put((
            self.process_audio_sync,
            (audio_path, target_language, character),
            {},
            None
        ))
        
        return task_id
    
    def process_text_input(self, text: str, source_language: str, target_language: str, character: str) -> Dict[str, Any]:
        """
        Process text input and generate a spoken response.
        
        Args:
            text (str): Input text
            source_language (str): Source language of the input
            target_language (str): Target language for the response
            character (str): Character to use for TTS
            
        Returns:
            Dict[str, Any]: Result of the operation
        """
        try:
            # Process the text input using the voice assistant
            response_text = self.voice_assistant.process_text_input(text, source_language, target_language)
            
            # Generate speech from the response
            timestamp = int(time.time())
            filename = f"{character}_{target_language}_{timestamp}.mp3"
            
            # Convert response to speech
            result = self.tts_system.generate_speech(response_text, character, target_language, filename)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Text processed successfully",
                    "response_text": response_text,
                    "audio_file": f"/audio/{result['filename']}"
                }
            else:
                return {
                    "success": False,
                    "error": result.get('error', "TTS generation failed")
                }
        except Exception as e:
            logger.error(f"Error processing text: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_characters_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Get character data for the UI.
        
        Returns:
            Dict[str, Dict[str, Any]]: Character data
        """
        return self.tts_system.get_characters_data()
    
    def get_supported_languages(self, character: str) -> Dict[str, Any]:
        """
        Get supported languages for a character.
        
        Args:
            character (str): Character name
            
        Returns:
            Dict[str, Any]: Result with languages or error
        """
        return self.tts_system.get_supported_languages(character)