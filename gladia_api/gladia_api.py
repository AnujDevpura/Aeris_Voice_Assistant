import os
import time
import requests

API_KEY = '3b39a68e-a06b-4944-ac53-92e6dac7b9f5'
UPLOAD_URL = 'https://api.gladia.io/v2/upload'
TRANSCRIPTION_URL = 'https://api.gladia.io/v2/transcription'
POLL_INTERVAL = 5  # seconds between polling
MAX_RETRIES = 60  # maximum number of retries (5 minutes total)

def upload_audio(filename):
    headers = {'x-gladia-key': API_KEY}
    files = {'audio': (filename, open(filename, 'rb'), 'audio/wav')}
    
    try:
        response = requests.post(UPLOAD_URL, headers=headers, files=files)
        response.raise_for_status()
        
        audio_url = response.json().get('audio_url')
        print(f"Audio uploaded. URL: {audio_url}")
        return audio_url
    except Exception as e:
        print(f"Failed to upload audio: {str(e)}")
        return None

def request_transcription(audio_url):
    headers = {
        'Content-Type': 'application/json',
        'x-gladia-key': API_KEY
    }
    data = {
        "audio_url": audio_url,
        "sentences": False,
        "subtitles": False,
        "moderation": False,
        "diarization": False,
        "translation": False,
        "audio_to_llm": False,
        "display_mode": False,
        "summarization": False,
        "audio_enhancer": True,
        "chapterization": False,
        "custom_spelling": False,
        "detect_language": True,  # Make sure this is True for language detection
        "name_consistency": False,
        "sentiment_analysis": False,
        "diarization_enhanced": False,
        "punctuation_enhanced": False,
        "enable_code_switching": False,
        "named_entity_recognition": False,
        "speaker_reidentification": False,
        "accurate_words_timestamps": False,
        "skip_channel_deduplication": False,
        "structured_data_extraction": False
    }
    
    try:
        response = requests.post(TRANSCRIPTION_URL, headers=headers, json=data)
        response.raise_for_status()
        
        job_id = response.json().get('id')
        print(f"Transcription requested. Job ID: {job_id}")
        return job_id
    except Exception as e:
        print(f"Failed to request transcription: {str(e)}")
        return None

def check_transcription_status(job_id):
    headers = {'x-gladia-key': API_KEY}
    get_url = f"https://api.gladia.io/v2/transcription/{job_id}"
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(get_url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            status = result.get('status')
            
            # The API returns 'done' when complete, not 'completed'
            if status == "done":
                print("Transcription completed.")
                return result
            elif status == "error" or result.get('error_code'):
                error_message = result.get('error_code', 'Unknown error')
                print(f"Transcription failed: {error_message}")
                return None
            else:  # queued or processing
                print(f"Transcription in progress ({retries+1}/{MAX_RETRIES}). Status: {status}. Retrying in {POLL_INTERVAL} seconds...")
                time.sleep(POLL_INTERVAL)
                retries += 1
                
        except Exception as e:
            print(f"Error checking transcription: {str(e)}")
            time.sleep(POLL_INTERVAL)
            retries += 1
    
    print(f"Timeout after {MAX_RETRIES} retries.")
    return None

def find_in_dict(data, key, path=''):
    """Recursively search for a key in a nested dictionary."""
    if isinstance(data, dict):
        if key in data:
            return data[key], path + '.' + key if path else key
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                result, found_path = find_in_dict(v, key, path + '.' + k if path else k)
                if result is not None:
                    return result, found_path
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                result, found_path = find_in_dict(item, key, f"{path}[{i}]")
                if result is not None:
                    return result, found_path
    return None, ''

def transcribe_audio(file_path):
    print(f"Starting transcription for: {file_path}")
    
    audio_url = upload_audio(file_path)
    if not audio_url:
        print("Failed to upload audio.")
        return None, None
    
    job_id = request_transcription(audio_url)
    if not job_id:
        print("Failed to request transcription.")
        return None, None
    
    transcription_result = check_transcription_status(job_id)
    if transcription_result:
        try:
            # Extract transcript from result.transcription.full_transcript
            transcript = transcription_result.get('result', {}).get('transcription', {}).get('full_transcript')
            
            if not transcript:
                # If not found in the expected location, search through the entire response
                transcript, path = find_in_dict(transcription_result, 'full_transcript')
                print(f"Found transcript at: {path}")
            
            # Look for language information in several possible locations
            language = None
            
            # Try the primary location first
            language = transcription_result.get('result', {}).get('transcription', {}).get('language')
            
            # If not found, try the detected_language field
            if not language:
                language = transcription_result.get('result', {}).get('transcription', {}).get('detected_language')
            
            # If still not found, try metadata
            if not language:
                language = transcription_result.get('result', {}).get('metadata', {}).get('language')
            
            # If still not found, search for any field with "language" in its name
            if not language:
                for field in ['language', 'detected_language', 'spoken_language']:
                    language_value, path = find_in_dict(transcription_result, field)
                    if language_value:
                        language = language_value
                        print(f"Found language at: {path}")
                        break
            
            # Ensure language is in a list format
            if language:
                if isinstance(language, str):
                    languages = [language]
                elif isinstance(language, list):
                    languages = language
                else:
                    languages = []
            else:
                # If no language was found, try to infer it from other data
                # Such as locale or region information
                locale, _ = find_in_dict(transcription_result, 'locale')
                if locale and isinstance(locale, str):
                    languages = [locale.split('-')[0]]  # e.g., extract 'en' from 'en-US'
                else:
                    languages = []
            
            language_str = ', '.join(languages) if languages else 'Unknown'
            
            print(f"Transcription completed. Detected language(s): {language_str}")
            return transcript, language_str
        except Exception as e:
            print(f"Error extracting transcription data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    else:
        print("Failed to get transcription result.")
        return None, None

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input("Enter the path to your audio file: ")
    
    transcript, languages = transcribe_audio(file_path)
    
    if transcript:
        print("\nTranscription:")
        print("-" * 80)
        print(transcript)
        print("-" * 80)
        print(f"Detected language(s): {languages}")
    else:
        print("Transcription failed.")