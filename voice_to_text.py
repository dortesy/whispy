#!/usr/bin/env python3

import os
import sys
import time
import tempfile
import subprocess
import sounddevice as sd
import requests
from pathlib import Path
from dotenv import load_dotenv
import scipy.io.wavfile as wav
import numpy as np

load_dotenv()

class VoiceToText:
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            print("Error: GROQ_API_KEY environment variable not set")
            sys.exit(1)
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        
        # Audio settings
        self.sample_rate = 16000
        self.duration = 8  # seconds
        self.channels = 1
    
    def record_audio(self):
        """Record audio from default microphone"""
        print("🎤 Recording... (8 seconds)")
        
        try:
            # Record audio
            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16
            )
            sd.wait()  # Wait for recording to complete
            
            # Save to temporary WAV file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            wav.write(temp_file.name, self.sample_rate, audio_data)
            
            print("✅ Recording complete")
            return temp_file.name
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path):
        """Send audio to Groq API for transcription"""
        print("🔄 Transcribing audio...")
        
        try:
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': ('audio.wav', audio_file, 'audio/wav'),
                    'model': (None, 'whisper-large-v3'),
                    'language': (None, 'en'),
                    'response_format': (None, 'text')
                }
                
                response = requests.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    transcription = response.text.strip()
                    print(f"📝 Transcription: {transcription}")
                    return transcription
                else:
                    print(f"❌ Transcription failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def improve_text(self, text):
        """Send transcribed text to Groq API for improvement"""
        print("✨ Improving text...")
        
        system_prompt = """You are an expert technical writer and native English speaker. Your task is to take voice transcriptions and transform them into polished, professional text that sounds natural and well-written.

Instructions:
- Fix grammar, spelling, and punctuation errors
- Improve clarity, flow, and readability
- Make the text sound professional and articulate
- Preserve all technical terms and concepts accurately
- Remove filler words (um, uh, like, you know, etc.)
- Ensure proper sentence structure and transitions
- Keep the same meaning and intent as the original
- Output only the improved text, no explanations or metadata"""

        try:
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                improved_text = response.json()['choices'][0]['message']['content'].strip()
                print(f"✨ Improved text: {improved_text}")
                return improved_text
            else:
                print(f"❌ Text improvement failed: {response.status_code} - {response.text}")
                return text  # Return original if improvement fails
                
        except Exception as e:
            print(f"❌ Text improvement error: {e}")
            return text  # Return original if improvement fails
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard using wl-clipboard"""
        try:
            process = subprocess.Popen(
                ['wl-copy'],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text)
            
            if process.returncode == 0:
                print("📋 Text copied to clipboard")
                return True
            else:
                print("❌ Failed to copy to clipboard")
                return False
                
        except Exception as e:
            print(f"❌ Clipboard error: {e}")
            return False
    
    def cleanup_temp_file(self, file_path):
        """Clean up temporary audio file"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"⚠️  Failed to cleanup temp file: {e}")
    
    def run(self):
        """Execute the complete voice-to-text workflow"""
        print("🚀 Starting voice-to-text workflow...")
        
        # Step 1: Record audio
        audio_file = self.record_audio()
        if not audio_file:
            return False
        
        try:
            # Step 2: Transcribe audio
            transcription = self.transcribe_audio(audio_file)
            if not transcription:
                return False
            
            # Step 3: Improve text
            improved_text = self.improve_text(transcription)
            
            # Step 4: Copy to clipboard
            success = self.copy_to_clipboard(improved_text)
            
            print("🎉 Workflow completed successfully!")
            return success
            
        finally:
            # Always cleanup temp file
            self.cleanup_temp_file(audio_file)

def main():
    """Main entry point"""
    try:
        vtt = VoiceToText()
        success = vtt.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()