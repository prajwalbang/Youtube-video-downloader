import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
import threading
import subprocess
import shutil
import json
import sys
import os
try:
    import yt_dlp
except ImportError:
    print("yt-dlp not installed. Install it with: pip install yt-dlp")
    exit()


# Codecs QuickTime (and most players) can open inside an mp4
PLAYABLE_VIDEO = {"h264", "hevc"}
PLAYABLE_AUDIO = {"aac", "mp3", "alac"}

# Higher is more widely playable; VP9 doesn't play in QuickTime at all
CODEC_RANK = {"H.264": 3, "HEVC": 2, "AV1": 1}


def codec_label(vcodec):
    """Friendly name for a yt-dlp codec string like 'avc1.64002a' or 'vp09.00.41.08'."""
    vcodec = (vcodec or "").lower()
    if vcodec.startswith(("avc1", "h264")):
        return "H.264"
    if vcodec.startswith(("hev1", "hvc1", "h265")):
        return "HEVC"
    if vcodec.startswith("av01"):
        return "AV1"
    if vcodec.startswith(("vp09", "vp9")):
        return "VP9"
    return vcodec.split(".")[0].upper() or "Unknown"


def audio_codec_label(acodec):
    """Friendly name for a yt-dlp audio codec string like 'mp4a.40.2' or 'opus'."""
    acodec = (acodec or "").lower()
    if acodec.startswith("mp4a"):
        return "AAC"
    if acodec.startswith("opus"):
        return "Opus"
    return acodec.split(".")[0].upper() or "Unknown"


def size_label(filesize):
    return f"{filesize / (1024 * 1024):.1f} MB" if filesize else "—"


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")

        # Download directory and formats storage
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.available_formats = []   # formats currently shown in the table
        self.video_formats = []
        self.audio_formats = []
        self.video_info = None
        self.save_as = tk.StringVar(value="mp4")
        self.last_file = None
        self.ffmpeg_available = shutil.which("ffmpeg") is not None

        self.setup_style()
        self.build_ui()

        # Size the window from the content so nothing is cut off, whatever the font scaling
        self.root.update_idletasks()
        min_height = self.root.winfo_reqheight()
        self.root.minsize(560, min_height)
        self.root.geometry(f"700x{min_height + 120}")

    def setup_style(self):
        style = ttk.Style()

        # Use the native macOS theme when available, with system colors that follow dark mode
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
            self.secondary_fg = "systemSecondaryLabelColor"
            self.primary_fg = "systemLabelColor"
        else:
            style.theme_use("clam")
            self.secondary_fg = "gray40"
            self.primary_fg = "black"
        self.error_fg = "#FF453A"

        family = tkfont.nametofont("TkDefaultFont").actual("family")
        self.fonts = {
            "title": tkfont.Font(family=family, size=24, weight="bold"),
            "subtitle": tkfont.Font(family=family, size=13),
            "section": tkfont.Font(family=family, size=13, weight="bold"),
            "body": tkfont.Font(family=family, size=13),
            "small": tkfont.Font(family=family, size=12),
        }

        style.configure("Title.TLabel", font=self.fonts["title"])
        style.configure("Subtitle.TLabel", font=self.fonts["subtitle"], foreground=self.secondary_fg)
        style.configure("Section.TLabel", font=self.fonts["section"])
        style.configure("Body.TLabel", font=self.fonts["body"])
        style.configure("Secondary.TLabel", font=self.fonts["small"], foreground=self.secondary_fg)
        style.configure("Treeview", rowheight=28, font=self.fonts["body"])
        style.configure("Treeview.Heading", font=self.fonts["small"])

    def build_ui(self):
        container = ttk.Frame(self.root, padding=(28, 24, 28, 24))
        container.pack(fill="both", expand=True)

        # Header
        ttk.Label(container, text="YouTube Downloader", style="Title.TLabel").pack(anchor="w")
        ttk.Label(container, text="Paste a link, pick a quality, and download.",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(2, 18))

        # URL input
        url_row = ttk.Frame(container)
        url_row.pack(fill="x")

        self.url_entry = ttk.Entry(url_row, font=self.fonts["body"])
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.url_entry.bind("<Return>", lambda e: self.fetch_formats())
        self.url_entry.focus_set()

        self.fetch_btn = ttk.Button(url_row, text="Fetch", command=self.fetch_formats)
        self.fetch_btn.pack(side="left", padx=(10, 0))

        # Video details, filled in after fetching
        self.video_label = ttk.Label(container, text="", style="Secondary.TLabel")
        self.video_label.pack(anchor="w", pady=(8, 0))

        # Formats table, with the Save as choice on the same row
        quality_row = ttk.Frame(container)
        quality_row.pack(fill="x", pady=(14, 6))
        ttk.Label(quality_row, text="Quality", style="Section.TLabel").pack(side="left")

        save_as_options = [("Video (MP4)", "mp4"), ("Audio (M4A)", "m4a"), ("Audio (MP3)", "mp3")]
        for text, value in reversed(save_as_options):
            option = ttk.Radiobutton(quality_row, text=text, value=value, variable=self.save_as,
                                     command=self.populate_table)
            option.pack(side="right", padx=(12, 0))
            if value == "mp3" and not self.ffmpeg_available:
                option.state(["disabled"])   # MP3 needs FFmpeg to convert
        ttk.Label(quality_row, text="Save as:", style="Secondary.TLabel").pack(side="right")

        # Packed last (see end of build_ui) so it only takes space left over by the other sections
        table_frame = ttk.Frame(container)

        columns = {
            "resolution": ("Resolution", 100),
            "fps": ("FPS", 95),
            "format": ("Codec", 130),
            "size": ("Size", 100),
            "audio": ("Audio", 170),
        }
        self.format_table = ttk.Treeview(table_frame, columns=list(columns),
                                         show="headings", selectmode="browse", height=6)
        for col, (heading, width) in columns.items():
            self.format_table.heading(col, text=heading, anchor="w")
            self.format_table.column(col, width=width, anchor="w", stretch=(col == "audio"))

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.format_table.yview)
        self.format_table.configure(yscrollcommand=scrollbar.set)
        self.format_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.format_table.bind("<<TreeviewSelect>>", self.on_select)
        self.format_table.bind("<Double-1>", lambda e: self.start_download())

        # Save location
        save_label = ttk.Label(container, text="Save to", style="Section.TLabel")
        path_row = ttk.Frame(container)

        self.path_label = ttk.Label(path_row, text=self.display_path(self.download_path),
                                    style="Body.TLabel")
        self.path_label.pack(side="left")

        ttk.Button(path_row, text="Choose…", command=self.browse_folder).pack(side="right")

        separator = ttk.Separator(container)

        # Bottom bar: status and progress on the left, actions on the right
        bottom = ttk.Frame(container)

        self.download_btn = ttk.Button(bottom, text="Download", command=self.start_download,
                                       default="active")
        self.download_btn.state(["disabled"])
        self.download_btn.pack(side="right")

        reveal_text = "Show in Finder" if sys.platform == "darwin" else "Open Folder"
        self.reveal_btn = ttk.Button(bottom, text=reveal_text, command=self.reveal_file)

        status_col = ttk.Frame(bottom)
        status_col.pack(side="left", fill="x", expand=True, padx=(0, 20))

        self.status_label = ttk.Label(status_col, text="Enter a YouTube URL to get started.",
                                      style="Secondary.TLabel")
        self.status_label.pack(anchor="w")

        self.progress = ttk.Progressbar(status_col, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(6, 0))

        # Pack the lower sections from the bottom up, then let the table fill what's left,
        # so the table is what shrinks when the window is small
        bottom.pack(side="bottom", fill="x")
        separator.pack(side="bottom", fill="x", pady=18)
        path_row.pack(side="bottom", fill="x")
        save_label.pack(side="bottom", anchor="w", pady=(18, 6))
        table_frame.pack(fill="both", expand=True)

    # ---------- helpers ----------

    def display_path(self, path):
        home = os.path.expanduser("~")
        return "~" + path[len(home):] if path.startswith(home) else path

    def set_status(self, text, error=False):
        self.status_label.config(text=text, foreground=self.error_fg if error else self.secondary_fg)

    def set_busy(self, busy):
        state = ["disabled"] if busy else ["!disabled"]
        self.fetch_btn.state(state)
        if busy or self.format_table.selection():
            self.download_btn.state(state)

    def on_ui(self, func, *args):
        """Run func on the Tk main thread (safe to call from worker threads)."""
        self.root.after(0, func, *args)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.config(text=self.display_path(folder))

    def on_select(self, event=None):
        if self.format_table.selection() and not self.fetch_btn.instate(["disabled"]):
            self.download_btn.state(["!disabled"])

    def reveal_file(self):
        if not self.last_file:
            return
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", self.last_file])
        elif os.name == "nt":
            subprocess.run(["explorer", "/select,", self.last_file])
        else:
            subprocess.run(["xdg-open", os.path.dirname(self.last_file)])

    # ---------- fetching formats ----------

    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("No URL", "Please paste a YouTube URL first.")
            return

        self.set_busy(True)
        self.download_btn.state(["disabled"])
        self.reveal_btn.pack_forget()
        self.format_table.delete(*self.format_table.get_children())
        self.video_label.config(text="")
        self.progress.config(mode="indeterminate")
        self.progress.start(12)
        self.set_status("Fetching available formats…")

        threading.Thread(target=self.get_video_formats, args=(url,), daemon=True).start()

    def get_video_formats(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Filter and organize formats
            video_formats = []
            for f in info.get('formats', []):
                # Only include formats with video
                if f.get('vcodec') != 'none' and f.get('height'):
                    fps = f.get('fps') or 30
                    filesize = f.get('filesize') or f.get('filesize_approx') or 0
                    has_audio = f.get('acodec') != 'none'

                    if has_audio:
                        audio_str = "Included"
                    elif self.ffmpeg_available:
                        audio_str = "Merged automatically"
                    else:
                        audio_str = "None (FFmpeg missing)"

                    # Codecs QuickTime can't play get converted to H.264 after downloading
                    codec = codec_label(f.get('vcodec'))
                    if codec in ("H.264", "HEVC") or not self.ffmpeg_available:
                        codec_str = codec
                    else:
                        codec_str = f"{codec} → H.264"

                    video_formats.append({
                        'format_id': f.get('format_id'),
                        'resolution': f['height'],
                        'fps': fps,
                        'codec_rank': CODEC_RANK.get(codec, 0),
                        'bitrate': f.get('tbr') or 0,
                        'has_audio': has_audio,
                        'values': (
                            f"{f['height']}p",
                            f"{fps:g}",
                            codec_str,
                            size_label(filesize),
                            audio_str,
                        ),
                    })

            # Sort by resolution, fps, then the most playable codec and bitrate,
            # so each resolution keeps its best version (preferring H.264 over VP9/AV1)
            video_formats.sort(key=lambda x: (x['resolution'], x['fps'], x['codec_rank'], x['bitrate']),
                               reverse=True)

            # Remove duplicates with same resolution and audio status
            seen = set()
            unique_formats = []
            for fmt in video_formats:
                key = (fmt['resolution'], fmt['has_audio'])
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(fmt)

            # Audio-only formats, for saving as M4A or MP3
            audio_formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') == 'none' and f.get('acodec') not in (None, 'none'):
                    format_id = f.get('format_id', '')
                    audio_formats.append({
                        'format_id': format_id,
                        'codec': audio_codec_label(f.get('acodec')),
                        'bitrate': f.get('abr') or f.get('tbr') or 0,
                        'sample_rate': f.get('asr') or 0,
                        'size': size_label(f.get('filesize') or f.get('filesize_approx')),
                        # Prefer the original language and skip volume-normalized (DRC) copies
                        'preference': (f.get('language_preference') or 0, 'drc' not in format_id),
                    })

            # Keep one entry per codec and bitrate level, highest bitrate first
            audio_formats.sort(key=lambda x: (x['preference'], x['bitrate']), reverse=True)
            seen = set()
            unique_audio = []
            for fmt in audio_formats:
                key = (fmt['codec'], round(fmt['bitrate'], -1))
                if key not in seen:
                    seen.add(key)
                    unique_audio.append(fmt)
            unique_audio.sort(key=lambda x: x['bitrate'], reverse=True)

            self.on_ui(self.show_formats, info, unique_formats, unique_audio)

        except Exception as e:
            self.on_ui(self.fetch_failed, str(e))

    def show_formats(self, info, video_formats, audio_formats):
        self.video_info = info
        self.video_formats = video_formats
        self.audio_formats = audio_formats

        self.progress.stop()
        self.progress.config(mode="determinate", value=0)

        details = [info.get('title', 'Untitled')]
        if info.get('uploader'):
            details.append(info['uploader'])
        if info.get('duration_string'):
            details.append(info['duration_string'])
        self.video_label.config(text="  ·  ".join(details))

        self.set_busy(False)
        self.populate_table()
        if video_formats or audio_formats:
            self.set_status("Choose a format and click Download.")
        else:
            self.set_status("No downloadable formats found.", error=True)

    def populate_table(self):
        """Fill the table with video or audio formats, depending on the Save as choice."""
        mode = self.save_as.get()
        table = self.format_table
        table.delete(*table.get_children())

        if mode == "mp4":
            headings = ("Resolution", "FPS", "Codec", "Size", "Audio")
            formats = self.video_formats
            rows = [fmt['values'] for fmt in formats]
        else:
            headings = ("Bitrate", "Sample Rate", "Codec", "Size", "Output")
            # Without FFmpeg only AAC can be saved (as M4A, no conversion needed)
            formats = [f for f in self.audio_formats if self.ffmpeg_available or f['codec'] == "AAC"]
            if mode == "m4a":
                # AAC goes into M4A without re-encoding, so list it first
                formats = sorted(formats, key=lambda f: (f['codec'] == "AAC", f['bitrate']), reverse=True)

            rows = []
            for fmt in formats:
                if mode == "m4a" and fmt['codec'] == "AAC":
                    output = "M4A, no conversion"
                else:
                    output = f"Converted to {mode.upper()}"
                rows.append((
                    f"{fmt['bitrate']:.0f} kbps" if fmt['bitrate'] else "—",
                    f"{fmt['sample_rate'] / 1000:g} kHz" if fmt['sample_rate'] else "—",
                    fmt['codec'],
                    fmt['size'],
                    output,
                ))

        for col, heading in zip(table["columns"], headings):
            table.heading(col, text=heading)

        self.available_formats = formats
        for index, values in enumerate(rows):
            table.insert("", "end", iid=str(index), values=values)

        if formats:
            # Preselect the best option
            table.selection_set("0")
            table.focus("0")
        if formats and not self.fetch_btn.instate(["disabled"]):
            self.download_btn.state(["!disabled"])
        else:
            self.download_btn.state(["disabled"])

    def fetch_failed(self, error):
        self.progress.stop()
        self.progress.config(mode="determinate", value=0)
        self.set_busy(False)
        self.set_status("Couldn't fetch formats.", error=True)
        messagebox.showerror("Couldn't Fetch Formats", error)

    # ---------- downloading ----------

    def start_download(self):
        selection = self.format_table.selection()
        if not selection or self.fetch_btn.instate(["disabled"]):
            return

        mode = self.save_as.get()
        selected_format = self.available_formats[int(selection[0])]

        if not os.path.isdir(self.download_path):
            messagebox.showerror("Folder Not Found", "The download folder doesn't exist.")
            return

        if mode == "mp4" and not selected_format['has_audio'] and not self.ffmpeg_available:
            proceed = messagebox.askyesno(
                "Download Without Audio?",
                "FFmpeg isn't installed, so this video will be saved without sound.\n\n"
                "Install FFmpeg to merge audio automatically, or choose a format "
                "with audio included."
            )
            if not proceed:
                return

        self.set_busy(True)
        self.reveal_btn.pack_forget()
        self.progress.config(mode="determinate", value=0)
        self.set_status("Starting download…")

        threading.Thread(target=self.download_video, args=(selected_format, mode), daemon=True).start()

    def download_video(self, selected_format, mode):
        try:
            format_id = selected_format['format_id']

            ydl_opts = {
                'format': format_id,
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'noprogress': True,
                'progress_hooks': [self.on_progress],
                'postprocessor_hooks': [self.on_postprocess],
            }

            if mode == "mp4":
                if not selected_format['has_audio'] and self.ffmpeg_available:
                    # Download the best audio too and merge them into one mp4
                    ydl_opts['format'] = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
                    ydl_opts['merge_output_format'] = 'mp4'
            elif self.ffmpeg_available:
                # Save as M4A (AAC) or MP3; AAC sources are copied into M4A without re-encoding.
                # MP3 uses the best variable bitrate setting.
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': mode,
                    'preferredquality': '0' if mode == "mp3" else '192',
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.video_info['webpage_url'], download=True)

            downloads = info.get('requested_downloads') or [{}]
            filepath = downloads[0].get('filepath')
            if mode == "mp4" and filepath and self.ffmpeg_available:
                filepath = self.make_playable(filepath, info.get('duration'))
            no_audio = mode == "mp4" and not selected_format['has_audio'] and not self.ffmpeg_available

            self.on_ui(self.download_finished, info.get('title', 'video'), filepath, no_audio)

        except Exception as e:
            self.on_ui(self.download_failed, str(e))

    def make_playable(self, filepath, duration):
        """Re-encode to H.264/AAC mp4 if QuickTime can't play the downloaded codecs.
        Runs on the worker thread and returns the final file path."""
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name",
             "-of", "json", filepath],
            capture_output=True, text=True
        )
        streams = json.loads(probe.stdout or "{}").get("streams", [])
        convert_video = any(s["codec_name"] not in PLAYABLE_VIDEO
                            for s in streams if s.get("codec_type") == "video")
        convert_audio = any(s["codec_name"] not in PLAYABLE_AUDIO
                            for s in streams if s.get("codec_type") == "audio")
        if not (convert_video or convert_audio):
            return filepath

        self.on_ui(self.update_progress, 0, "Converting to H.264 for QuickTime…")

        base = os.path.splitext(filepath)[0]
        temp_path = base + ".converting.mp4"
        video_args = (["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
                      if convert_video else ["-c:v", "copy"])
        audio_args = ["-c:a", "aac", "-b:a", "192k"] if convert_audio else ["-c:a", "copy"]

        process = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-i", filepath, *video_args, *audio_args,
             "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", temp_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        # ffmpeg reports how far it has encoded as out_time_us=<microseconds>
        for line in process.stdout:
            if line.startswith("out_time_us=") and duration:
                try:
                    seconds = int(line.split("=")[1]) / 1_000_000
                except ValueError:
                    continue
                percent = max(0, min(seconds / duration * 100, 100))
                self.on_ui(self.update_progress, percent,
                           f"Converting to H.264 for QuickTime…  {percent:.0f}%")

        errors = process.stderr.read()
        if process.wait() != 0:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise RuntimeError(f"Converting the video failed:\n{errors.strip()}")

        final_path = base + ".mp4"
        os.replace(temp_path, final_path)
        if final_path != filepath:
            os.remove(filepath)
        return final_path

    def on_progress(self, d):
        # Called by yt-dlp on the worker thread
        if d['status'] != 'downloading':
            return

        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        percent = d.get('downloaded_bytes', 0) / total * 100 if total else 0
        part = "audio" if d.get('info_dict', {}).get('vcodec') == 'none' else "video"

        text = f"Downloading {part}…  {percent:.0f}%"
        if d.get('speed'):
            text += f"  ·  {d['speed'] / (1024 * 1024):.1f} MB/s"

        self.on_ui(self.update_progress, percent, text)

    def on_postprocess(self, d):
        if d['status'] != 'started':
            return
        if d.get('postprocessor') == 'Merger':
            self.on_ui(self.update_progress, 100, "Merging audio and video…")
        elif d.get('postprocessor') == 'ExtractAudio':
            self.on_ui(self.update_progress, 100, "Converting audio…")

    def update_progress(self, percent, text):
        self.progress.config(value=percent)
        self.set_status(text)

    def download_finished(self, title, filepath, no_audio):
        self.progress.config(value=100)
        self.set_busy(False)
        self.last_file = filepath

        note = " (no audio)" if no_audio else ""
        self.set_status(f"✓ Saved “{title}”{note}")
        if filepath:
            self.reveal_btn.pack(side="right", padx=(0, 10))

    def download_failed(self, error):
        self.progress.config(value=0)
        self.set_busy(False)
        self.set_status("Download failed.", error=True)
        messagebox.showerror("Download Failed", error)


def main():
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
