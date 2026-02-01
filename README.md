# YouTube Video Downloader

A simple, user-friendly Python GUI application for downloading YouTube videos in your preferred resolution.

## Features

✅ **Resolution Selection** - View and choose from all available video qualities  
✅ **Quality Information** - See resolution, file size, FPS, and audio availability  
✅ **Easy-to-Use GUI** - Simple interface built with Tkinter  
✅ **FFmpeg Auto-Detection** - Works with or without FFmpeg installed  
✅ **Custom Download Location** - Save videos wherever you want  
✅ **Progress Tracking** - Visual feedback during downloads  

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/youtube-downloader.git
cd youtube-downloader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python youtube_downloader.py
```

2. Paste a YouTube URL
3. Click "Fetch Resolutions"
4. Select your preferred quality
5. Click "Download Selected"

## Requirements

- Python 3.7+
- yt-dlp
- tkinter (usually included with Python)
- FFmpeg (optional, for merging high-quality video with audio)

### Installing FFmpeg (Optional)

For the highest quality downloads:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## Notes

- Formats marked "with audio" work without FFmpeg
- "Video only" formats require FFmpeg to merge with audio
- Without FFmpeg, you can still download video-only files (no sound)

## License

MIT License

## Disclaimer

This tool is for personal use only. Please respect YouTube's Terms of Service and copyright laws.
```

---

**Topics/Tags to add:**
```
youtube, downloader, python, gui, tkinter, yt-dlp, video-downloader, youtube-dl
