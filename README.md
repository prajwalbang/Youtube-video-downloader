# YouTube Video Downloader

A simple, user-friendly Python GUI application for downloading YouTube videos in your preferred resolution.

## Features

✅ **Resolution Selection** - View and choose from all available video qualities  
✅ **Quality Information** - See resolution, file size, FPS, and audio availability  
✅ **Automatic Audio Merging** - HD formats are downloaded with their audio and joined into one MP4  
✅ **Native Look** - Clean Tkinter interface that uses the native macOS theme and follows dark mode  
✅ **Live Progress** - Download percentage and speed, plus a "Show in Finder" button when done  
✅ **FFmpeg Auto-Detection** - Works with or without FFmpeg installed  
✅ **Custom Download Location** - Save videos wherever you want  

## Requirements

- **Python 3.10+** with tkinter (current yt-dlp no longer supports older Python)
- **Deno** - JavaScript runtime yt-dlp needs to read YouTube's full list of formats
- **FFmpeg** - recommended, for merging HD video with audio
- **yt-dlp** - installed from `requirements.txt`

> **macOS note:** the built-in `/usr/bin/python3` is Python 3.9 and is too old. Install a newer Python with Homebrew (see below).

## Installation

### 1. Install system dependencies

**macOS** (Homebrew):
```bash
brew install python@3.13 python-tk@3.13 ffmpeg deno
```

**Windows**:
- Python 3.10+ from [python.org](https://www.python.org/downloads/) (includes tkinter)
- FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)
- Deno: `winget install DenoLand.Deno`

**Linux** (Debian/Ubuntu):
```bash
sudo apt install python3 python3-venv python3-tk ffmpeg
curl -fsSL https://deno.land/install.sh | sh
```

### 2. Clone the repository
```bash
git clone https://github.com/prajwalbang/Youtube-video-downloader.git
cd Youtube-video-downloader
```

### 3. Create a virtual environment and install Python packages

macOS / Linux:
```bash
python3.13 -m venv .venv        # or any Python 3.10+
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

1. Activate the virtual environment (once per terminal session) and run the app:
```bash
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python youtube_downloader.py
```

2. Paste a YouTube URL and press Return (or click "Fetch")
3. Select your preferred quality (the highest is preselected)
4. Click "Download" (or double-click a row)

## How Audio Works

YouTube stores HD video (roughly above 360p) and audio as separate streams. The **Audio** column in the format table shows:

- **Included** - video and sound in one file, no FFmpeg needed
- **Merged automatically** - video-only stream; the app also downloads the best audio and joins them into one MP4 with FFmpeg
- **None (FFmpeg missing)** - shown when FFmpeg isn't installed; the download will have no sound

## Troubleshooting

- **Nothing happens / "yt-dlp not installed"** - the virtual environment isn't active, or you're running a different Python. Activate `.venv` first.
- **Missing resolutions or "Sign in to confirm you're not a bot"** - update yt-dlp (`pip install -U "yt-dlp[default]"`) and make sure Deno is installed.

## License

MIT License

## Disclaimer

This tool is for personal use only. Please respect YouTube's Terms of Service and copyright laws.
