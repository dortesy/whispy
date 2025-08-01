# Whispy - Voice-to-Text for Hyprland

A professional voice-to-text system optimized for Arch Linux with Hyprland, featuring real-time recording, AI-powered transcription, and intelligent text improvement using KIMI K2.

## ✨ Features

- **🎤 Toggle Recording**: Press hotkey to start/stop recording anywhere
- **⚡ Real-time Feedback**: Visual notifications and waybar integration
- **🎯 Smart Output**: Choose between clipboard, cursor insertion, or both
- **🧠 AI Enhancement**: KIMI K2 improves transcription quality and fixes technical terms
- **🔄 Flexible Processing**: Instant, improved, or progressive text processing
- **📱 Wayland Native**: Full integration with modern Linux desktop
- **⚙️ Configurable**: Environment-based configuration for all options

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# System packages
sudo pacman -S python python-pip wl-clipboard wtype pipewire-pulse

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Python packages
pip install sounddevice requests python-dotenv scipy numpy
```

### 2. Configure API

1. Get your Groq API key from [console.groq.com/keys](https://console.groq.com/keys)
2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and add your key:
   ```bash
   GROQ_API_KEY=your_actual_api_key_here
   ```

### 3. Set Up Hyprland Hotkey

Add to your `~/.config/hypr/hyprland.conf`:

```conf
bind = SUPER SHIFT, S, exec, /path/to/whispy/venv/bin/python /path/to/whispy/voice_recorder.py
```

Replace `/path/to/whispy` with your actual project path.

### 4. Reload and Test

```bash
# Reload Hyprland config
hyprctl reload

# Test manually
./venv/bin/python voice_recorder.py
```

## 🎯 Usage

### Basic Recording
1. **Start**: Press `SUPER + SHIFT + S` 
2. **Speak**: Record your voice (unlimited duration)
3. **Stop**: Press `SUPER + SHIFT + S` again
4. **Result**: Text appears where you need it

### Output Modes
Configure in `.env`:
- `OUTPUT_MODE=clipboard` - Copy to clipboard only
- `OUTPUT_MODE=insert` - Insert at cursor position
- `OUTPUT_MODE=both` - Copy AND insert (default)

### Processing Modes
- `PROCESSING_MODE=improved` - Wait for AI enhancement (default)
- `PROCESSING_MODE=instant` - Show raw transcription immediately
- `PROCESSING_MODE=both` - Show raw first, then replace with improved

## 🧠 AI Enhancement

Whispy uses **KIMI K2** (moonshotai/kimi-k2-instruct) to:
- Fix grammar and spelling errors
- Improve clarity and flow
- Correct technical terminology
- Remove filler words
- Enhance professional tone
- Preserve original meaning

## 🎛️ Waybar Integration

Add to your waybar config for visual status:

```json
"custom/whispy": {
  "exec": "/path/to/whispy/venv/bin/python /path/to/whispy/voice_recorder.py --status",
  "exec-if": "test -f ~/.whispy_waybar", 
  "return-type": "json",
  "interval": 1,
  "format": "{}",
  "on-click": "/path/to/whispy/venv/bin/python /path/to/whispy/voice_recorder.py",
  "tooltip": true
}
```

Status indicators:
- `🔴 REC` - Currently recording
- `⚡ PROC` - Processing audio
- *(empty)* - Ready/idle

## 🔧 Configuration

All settings in `.env`:

```bash
# Required
GROQ_API_KEY=your_key_here

# Output behavior (default: both)
OUTPUT_MODE=clipboard|insert|both

# Processing flow (default: improved) 
PROCESSING_MODE=improved|instant|both
```

## 🔄 Architecture

```
Audio Input → Recording Buffer → Transcription (Whisper) → Enhancement (KIMI K2) → Output
     ↓              ↓                    ↓                      ↓             ↓
Microphone    WAV Encoding         Groq API            AI Improvement    Clipboard/Insert
```

## 🛠️ Troubleshooting

### Audio Issues
```bash
# Check PipeWire
systemctl --user status pipewire-pulse

# Test microphone
arecord -d 3 test.wav && aplay test.wav
```

### API Problems
- Verify Groq API key in `.env`
- Check internet connection
- Ensure API credits available
- Try different model if quota exceeded

### Clipboard/Insert Issues
```bash
# Test Wayland clipboard
echo "test" | wl-copy && wl-paste

# Test wtype
wtype "hello world"
```

### Hotkey Not Working
- Check script path in `hyprland.conf`
- Verify script permissions: `chmod +x voice_recorder.py`
- Test manual execution
- Check Hyprland logs: `hyprctl logs`

### Process Management
```bash
# Check if recording is stuck
python voice_recorder.py --status

# Kill any stuck processes
pkill -f voice_recorder.py
```

## 📊 Performance

- **Latency**: 1-4 seconds (network dependent)
- **Memory**: <30MB during operation
- **CPU**: Minimal impact
- **Recording**: No duration limits
- **Accuracy**: 95%+ with clear audio

## 🎨 Customization

### Custom Hotkeys
```conf
# Alternative bindings in hyprland.conf
bind = SUPER, V, exec, /path/to/whispy/venv/bin/python /path/to/whispy/voice_recorder.py
bind = CTRL ALT, R, exec, /path/to/whispy/venv/bin/python /path/to/whispy/voice_recorder.py
```

### Desktop Integration
- Creates `~/.whispy_state` for process tracking
- Creates `~/.whispy_waybar` for status display
- Uses system notifications for feedback

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make your changes
4. Test on Arch Linux + Hyprland
5. Submit pull request

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com) for fast AI inference
- [Whisper](https://openai.com/whisper) for speech recognition
- [KIMI K2](https://www.moonshot.cn/) for text enhancement
- [Hyprland](https://hyprland.org) for the amazing compositor