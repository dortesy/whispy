#!/usr/bin/env python3

import os
import sys
import time
import tempfile
import subprocess
import sounddevice as sd
import requests
import threading
from pathlib import Path
from dotenv import load_dotenv
import scipy.io.wavfile as wav
import numpy as np
import tkinter as tk
from tkinter import ttk

load_dotenv()

class ProgressWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Voice to Text")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Make window stay on top and center it
        self.root.attributes('-topmost', True)
        self.center_window()
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create widgets
        self.setup_widgets()
        
        # Bind escape key to close
        self.root.bind('<Escape>', lambda e: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (200 // 2)
        self.root.geometry(f"400x200+{x}+{y}")
    
    def setup_widgets(self):
        """Create and layout GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="🎤 Voice to Text", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Initializing...", font=('Arial', 12))
        self.status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, length=350, mode='indeterminate')
        self.progress.grid(row=2, column=0, columnspan=2, pady=(0, 20))
        
        # Result text area
        self.result_text = tk.Text(main_frame, height=4, width=45, wrap=tk.WORD, font=('Arial', 10))
        self.result_text.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # Scrollbar for text area
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.result_text.yview)
        scrollbar.grid(row=3, column=2, sticky="ns")
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        # Close button
        self.close_button = ttk.Button(main_frame, text="Close", command=self.close)
        self.close_button.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        self.close_button.configure(state='disabled')
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update()
    
    def update_result(self, text):
        """Update result text area"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, text)
        self.root.update()
    
    def start_progress(self):
        """Start progress bar animation"""
        self.progress.start(10)
    
    def stop_progress(self):
        """Stop progress bar animation"""
        self.progress.stop()
    
    def enable_close(self):
        """Enable close button"""
        self.close_button.configure(state='normal')
    
    def close(self):
        """Close the window"""
        self.root.quit()
        self.root.destroy()

class VoiceToTextGUI:
    def __init__(self, progress_window):
        self.progress_window = progress_window
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            self.progress_window.update_status("❌ Error: GROQ_API_KEY not set")
            self.progress_window.enable_close()
            return
        
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
        self.progress_window.update_status("🎤 Recording... (8 seconds)")
        self.progress_window.start_progress()
        
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
            
            self.progress_window.update_status("✅ Recording complete")
            return temp_file.name
            
        except Exception as e:
            self.progress_window.update_status(f"❌ Recording failed: {e}")
            self.progress_window.stop_progress()
            return None
    
    def transcribe_audio(self, audio_file_path):
        """Send audio to Groq API for transcription"""
        self.progress_window.update_status("🔄 Transcribing audio...")
        
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
                    self.progress_window.update_status("📝 Transcription complete")
                    self.progress_window.update_result(f"Raw: {transcription}")
                    return transcription
                else:
                    error_msg = f"❌ Transcription failed: {response.status_code}"
                    self.progress_window.update_status(error_msg)
                    return None
                    
        except Exception as e:
            self.progress_window.update_status(f"❌ Transcription error: {e}")
            return None
    
    def improve_text(self, text):
        """Send transcribed text to Groq API for improvement"""
        self.progress_window.update_status("✨ Improving text...")
        
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
                self.progress_window.update_status("✨ Text improvement complete")
                self.progress_window.update_result(f"Improved: {improved_text}")
                return improved_text
            else:
                self.progress_window.update_status("⚠️ Text improvement failed, using original")
                return text  # Return original if improvement fails
                
        except Exception as e:
            self.progress_window.update_status(f"⚠️ Text improvement error, using original")
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
                self.progress_window.update_status("📋 Text copied to clipboard!")
                return True
            else:
                self.progress_window.update_status("❌ Failed to copy to clipboard")
                return False
                
        except Exception as e:
            self.progress_window.update_status(f"❌ Clipboard error: {e}")
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
        if not self.api_key:
            return False
        
        self.progress_window.update_status("🚀 Starting workflow...")
        
        # Step 1: Record audio
        audio_file = self.record_audio()
        if not audio_file:
            self.progress_window.enable_close()
            return False
        
        try:
            # Step 2: Transcribe audio
            transcription = self.transcribe_audio(audio_file)
            if not transcription:
                self.progress_window.enable_close()
                return False
            
            # Step 3: Improve text
            improved_text = self.improve_text(transcription)
            
            # Step 4: Copy to clipboard
            success = self.copy_to_clipboard(improved_text)
            
            self.progress_window.stop_progress()
            self.progress_window.enable_close()
            
            if success:
                # Auto-close after 3 seconds if successful
                self.progress_window.root.after(3000, self.progress_window.close)
            
            return success
            
        finally:
            # Always cleanup temp file
            self.cleanup_temp_file(audio_file)

def main():
    """Main entry point"""
    try:
        # Create progress window
        progress_window = ProgressWindow()
        
        # Create voice-to-text processor
        vtt = VoiceToTextGUI(progress_window)
        
        # Start processing in a separate thread
        def run_workflow():
            vtt.run()
        
        thread = threading.Thread(target=run_workflow, daemon=True)
        thread.start()
        
        # Start GUI main loop
        progress_window.root.mainloop()
        
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()