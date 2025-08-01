#!/usr/bin/env python3

import os
import sys
import json
import time
import tempfile
import subprocess
import sounddevice as sd
import requests
import threading
import signal
from pathlib import Path
from dotenv import load_dotenv
import scipy.io.wavfile as wav
import numpy as np

load_dotenv()

class VoiceRecorder:
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
        self.channels = 1
        
        # State management
        self.state_file = Path.home() / '.whispy_state'
        self.recording = False
        self.audio_buffer = []
        self.stream = None
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.cleanup_and_exit)
        signal.signal(signal.SIGINT, self.cleanup_and_exit)
        signal.signal(signal.SIGUSR1, self.stop_recording_signal)
    
    def is_process_running(self, pid):
        """Check if a process is actually running"""
        if not pid:
            return False
        try:
            os.kill(pid, 0)  # Send signal 0 to check if process exists
            return True
        except OSError:
            return False
    
    def get_state(self):
        """Get current recording state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Validate the PID is actually running
                    if state.get("recording", False) and state.get("pid"):
                        if not self.is_process_running(state["pid"]):
                            self.cleanup_state()
                            return {"recording": False, "pid": None}
                    return state
        except:
            pass
        return {"recording": False, "pid": None}
    
    def set_state(self, recording=False, pid=None):
        """Set current recording state"""
        state = {"recording": recording, "pid": pid}
        with open(self.state_file, 'w') as f:
            json.dump(state, f)
    
    def cleanup_state(self):
        """Clean up state file"""
        if self.state_file.exists():
            self.state_file.unlink()
    
    def stop_recording_signal(self, signum=None, frame=None):
        """Signal handler to stop recording"""
        print("📨 Received stop signal")
        self.recording = False  # This will break the while loop in start_recording
    
    def cleanup_and_exit(self, signum=None, frame=None):
        """Clean shutdown"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.cleanup_state()
        sys.exit(0)
    
    def show_notification(self, message, urgency="normal"):
        """Show desktop notification"""
        try:
            subprocess.run([
                'notify-send', 
                '-u', urgency,
                '-t', '2000',
                '🎤 Voice Recorder', 
                message
            ], check=False)
        except:
            pass
    
    def update_waybar(self, status):
        """Update waybar status (if waybar is configured)"""
        waybar_file = Path.home() / '.whispy_waybar'
        try:
            with open(waybar_file, 'w') as f:
                if status == "recording":
                    f.write('{"text": "🔴 REC", "class": "recording", "tooltip": "Recording audio..."}')
                elif status == "processing":
                    f.write('{"text": "⚡ PROC", "class": "processing", "tooltip": "Processing audio..."}')
                else:
                    f.write('{"text": "", "class": "idle", "tooltip": "Voice recorder ready"}')
        except:
            pass
    
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio recording"""
        if status:
            print(f"Audio callback status: {status}")
        if self.recording:
            self.audio_buffer.append(indata.copy())
    
    def start_recording(self):
        """Start audio recording and keep process alive"""
        if self.recording:
            return False
        
        print("🎤 Starting recording...")
        self.show_notification("Recording started", "low")
        self.update_waybar("recording")
        
        self.recording = True
        self.audio_buffer = []
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.int16,
                callback=self.audio_callback
            )
            self.stream.start()
            self.set_state(recording=True, pid=os.getpid())
            
            # Keep the process alive while recording
            print("🎤 Recording... Press SUPER+SHIFT+S again to stop")
            try:
                while self.recording:
                    time.sleep(0.1)
                    
                # Recording stopped, process the audio
                print("🎤 Recording stopped, processing...")
                return self.process_recording()
                
            except KeyboardInterrupt:
                print("\n🛑 Recording cancelled")
                self.stop_recording()
                return False
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            self.show_notification(f"Recording failed: {e}", "critical")
            self.recording = False
            self.update_waybar("idle")
            return False
    
    def stop_recording(self):
        """Stop audio recording and return audio data"""
        # Check if we have a stream and audio buffer, even if recording flag is False
        if not self.stream and not self.audio_buffer:
            return None
        
        print("⏹️ Stopping recording...")
        
        # Always set recording to False and clean up stream
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        if not self.audio_buffer:
            print("❌ No audio recorded")
            self.show_notification("No audio recorded", "critical")
            self.update_waybar("idle")
            self.set_state(recording=False)
            return None
        
        # Combine audio buffer
        audio_data = np.concatenate(self.audio_buffer, axis=0)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        wav.write(temp_file.name, self.sample_rate, audio_data)
        
        duration = len(audio_data) / self.sample_rate
        print(f"✅ Recorded {duration:.1f} seconds of audio")
        self.show_notification(f"Recorded {duration:.1f}s - Processing...", "normal")
        self.update_waybar("processing")
        
        self.set_state(recording=False)
        return temp_file.name
    
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
                    timeout=60
                )
                
                if response.status_code == 200:
                    transcription = response.text.strip()
                    print(f"📝 Transcription: {transcription[:100]}...")
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
        You are also a developer that knows all the terms, and if the tanscription has some invalid term (or the word that look invalid by context) you automatically find the actual word using only context.
        If you see that sentence does not make any sense you must fix it using context

Instructions:
- Fix grammar, spelling, and punctuation errors
- Improve clarity, flow, and readability
- Make it more easy to understand
- Make the text sound professional and articulate
- Preserve all technical terms and concepts accurately
- Remove filler words (um, uh, like, you know, etc.)
- Ensure proper sentence structure and transitions
- Keep the same meaning and intent as the original
- Output only the improved text, no explanations or metadata"""

        try:
            payload = {
                "model": "moonshotai/kimi-k2-instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.6,
                "reasoning_effort": "none",
                "max_tokens": 6000
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                improved_text = response.json()['choices'][0]['message']['content'].strip()
                print(f"✨ Improved text: {improved_text[:100]}...")
                return improved_text
            else:
                print(f"⚠️ Text improvement failed: {response.status_code}")
                return text
                
        except Exception as e:
            print(f"⚠️ Text improvement error: {e}")
            return text
    
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
                word_count = len(text.split())
                self.show_notification(f"✅ {word_count} words copied to clipboard", "normal")
                return True
            else:
                print("❌ Failed to copy to clipboard")
                self.show_notification("Failed to copy to clipboard", "critical")
                return False
                
        except Exception as e:
            print(f"❌ Clipboard error: {e}")
            self.show_notification(f"Clipboard error: {e}", "critical")
            return False
    
    def cleanup_temp_file(self, file_path):
        """Clean up temporary audio file"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"⚠️ Failed to cleanup temp file: {e}")
    
    def process_recording(self):
        """Process the completed recording"""
        audio_file = self.stop_recording()
        if not audio_file:
            self.update_waybar("idle")
            return False
        
        try:
            # Transcribe audio
            transcription = self.transcribe_audio(audio_file)
            if not transcription:
                self.show_notification("Transcription failed", "critical")
                self.update_waybar("idle")
                return False
            
            # Improve text
            improved_text = self.improve_text(transcription)
            
            # Copy to clipboard
            success = self.copy_to_clipboard(improved_text)
            
            self.update_waybar("idle")
            return success
            
        finally:
            self.cleanup_temp_file(audio_file)
    
    def toggle_recording(self):
        """Toggle recording state"""
        current_state = self.get_state()
        
        if current_state.get("recording", False):
            # Send signal to stop the recording process
            recording_pid = current_state.get("pid")
            if recording_pid and self.is_process_running(recording_pid):
                try:
                    os.kill(recording_pid, signal.SIGUSR1)  # Custom signal to stop recording
                    print("🛑 Stop signal sent to recording process")
                    return True
                except OSError as e:
                    print(f"❌ Failed to send stop signal: {e}")
                    return False
            else:
                return False
        else:
            # Start recording
            return self.start_recording()

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        # Status check mode
        recorder = VoiceRecorder()
        state = recorder.get_state()
        if state.get("recording", False):
            print("recording")
        else:
            print("idle")
        sys.exit(0)
    
    try:
        recorder = VoiceRecorder()
        success = recorder.toggle_recording()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
