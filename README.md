# Voice-to-Text Workflow for Hyprland

A minimalist, high-performance voice-to-text system optimized for Arch Linux with Hyprland.

## Features

- **Global hotkey trigger** (SUPER + SHIFT + S)
- **Visual progress feedback** with GUI window
- **8-second audio recording** from default microphone
- **Whisper-large-v3 transcription** via Groq API
- **AI text improvement** using Llama-3.1-70B for professional polish
- **Direct clipboard integration** with Wayland
- **Real-time status updates** showing current operation

## Installation

### 1. Install System Dependencies

```bash
sudo pacman -S python python-pip wl-clipboard pipewire-pulse
```

### 2. Create Virtual Environment and Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install sounddevice requests python-dotenv scipy numpy
```

### 3. Set Up API Key

1. Get your Groq API key from [https://console.groq.com/keys](https://console.groq.com/keys)
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and add your API key:
   ```bash
   GROQ_API_KEY=your_actual_api_key_here
   ```

### 4. Make Script Executable

```bash
chmod +x voice_to_text.py
```

### 5. Configure Hyprland

Add this line to your `~/.config/hypr/hyprland.conf`:

```conf
bind = SUPER SHIFT, S, exec, /home/dortes/projects/whispy/venv/bin/python /home/dortes/projects/whispy/voice_to_text_gui.py
```

**Note:** Replace the path with your actual project location if different.

### 6. Reload Hyprland Configuration

```bash
hyprctl reload
```

## Usage

1. Press `SUPER + SHIFT + S` anywhere in your system
2. A GUI window appears showing "Recording..." status
3. Speak clearly for up to 8 seconds (recording starts immediately)
4. Watch the progress: Recording → Transcribing → Improving → Copying
5. The polished text will be copied to your clipboard
6. Window auto-closes after success, or press ESC/Close button
7. Paste anywhere with `CTRL + V`

## Troubleshooting

**Audio not recording:**
- Check PipeWire status: `systemctl --user status pipewire-pulse`
- Test microphone: `arecord -d 3 test.wav && aplay test.wav`

**API errors:**
- Verify your Groq API key in `.env`
- Check internet connection
- Ensure API key has sufficient credits

**Clipboard not working:**
- Verify wl-clipboard: `echo "test" | wl-copy && wl-paste`
- Check Wayland environment variables

**Script not triggering:**
- Verify script path in hyprland.conf
- Check script permissions: `ls -la voice_to_text.py`
- Test manually: `./voice_to_text.py`

## Architecture

The system uses a simple pipeline:
1. **Recording**: sounddevice → WAV file
2. **Transcription**: WAV → Groq Whisper API → raw text
3. **Improvement**: raw text → Groq Llama API → polished text
4. **Output**: polished text → wl-copy → clipboard

## Performance

- **Total latency**: ~3-5 seconds (depends on internet speed)
- **Memory usage**: <50MB during operation
- **Dependencies**: Minimal Python stack only