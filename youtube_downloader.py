import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
import threading
import subprocess
import shutil
import sys
import os
try:
    import yt_dlp
except ImportError:
    print("yt-dlp not installed. Install it with: pip install yt-dlp")
    exit()


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")

        # Download directory and formats storage
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.available_formats = []
        self.video_info = None
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

        # Formats table
        ttk.Label(container, text="Quality", style="Section.TLabel").pack(anchor="w", pady=(14, 6))

        # Packed last (see end of build_ui) so it only takes space left over by the other sections
        table_frame = ttk.Frame(container)

        columns = {
            "resolution": ("Resolution", 110),
            "fps": ("FPS", 60),
            "format": ("Format", 80),
            "size": ("Size", 100),
            "audio": ("Audio", 180),
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

                    video_formats.append({
                        'format_id': f.get('format_id'),
                        'resolution': f['height'],
                        'fps': fps,
                        'bitrate': f.get('tbr') or 0,
                        'has_audio': has_audio,
                        'values': (
                            f"{f['height']}p",
                            f"{fps:g}",
                            f.get('ext', 'mp4').upper(),
                            f"{filesize / (1024 * 1024):.1f} MB" if filesize else "—",
                            audio_str,
                        ),
                    })

            # Sort by resolution, then fps and bitrate, so the best version of each resolution is kept
            video_formats.sort(key=lambda x: (x['resolution'], x['fps'], x['bitrate']), reverse=True)

            # Remove duplicates with same resolution and audio status
            seen = set()
            unique_formats = []
            for fmt in video_formats:
                key = (fmt['resolution'], fmt['has_audio'])
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(fmt)

            self.on_ui(self.show_formats, info, unique_formats)

        except Exception as e:
            self.on_ui(self.fetch_failed, str(e))

    def show_formats(self, info, formats):
        self.video_info = info
        self.available_formats = formats

        self.progress.stop()
        self.progress.config(mode="determinate", value=0)

        details = [info.get('title', 'Untitled')]
        if info.get('uploader'):
            details.append(info['uploader'])
        if info.get('duration_string'):
            details.append(info['duration_string'])
        self.video_label.config(text="  ·  ".join(details))

        for index, fmt in enumerate(formats):
            self.format_table.insert("", "end", iid=str(index), values=fmt['values'])

        self.set_busy(False)
        if formats:
            # Preselect the highest quality
            self.format_table.selection_set("0")
            self.format_table.focus("0")
            self.set_status(f"Found {len(formats)} formats. Choose one and click Download.")
        else:
            self.set_status("No downloadable video formats found.", error=True)

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

        selected_format = self.available_formats[int(selection[0])]

        if not os.path.isdir(self.download_path):
            messagebox.showerror("Folder Not Found", "The download folder doesn't exist.")
            return

        if not selected_format['has_audio'] and not self.ffmpeg_available:
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

        threading.Thread(target=self.download_video, args=(selected_format,), daemon=True).start()

    def download_video(self, selected_format):
        try:
            format_id = selected_format['format_id']

            if not selected_format['has_audio'] and self.ffmpeg_available:
                # Download the best audio too and merge them into one mp4
                format_string = f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
            else:
                format_string = format_id

            ydl_opts = {
                'format': format_string,
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'noprogress': True,
                'progress_hooks': [self.on_progress],
                'postprocessor_hooks': [self.on_postprocess],
            }

            if not selected_format['has_audio'] and self.ffmpeg_available:
                ydl_opts['merge_output_format'] = 'mp4'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.video_info['webpage_url'], download=True)

            downloads = info.get('requested_downloads') or [{}]
            filepath = downloads[0].get('filepath')
            no_audio = not selected_format['has_audio'] and not self.ffmpeg_available

            self.on_ui(self.download_finished, info.get('title', 'video'), filepath, no_audio)

        except Exception as e:
            self.on_ui(self.download_failed, str(e))

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
        if d['status'] == 'started' and d.get('postprocessor') == 'Merger':
            self.on_ui(self.update_progress, 100, "Merging audio and video…")

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
