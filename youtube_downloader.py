import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
try:
    import yt_dlp
except ImportError:
    print("yt-dlp not installed. Install it with: pip install yt-dlp")
    exit()


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("650x500")
        self.root.resizable(False, False)
        
        # Download directory and formats storage
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.available_formats = []
        self.video_info = None
        
        # Title
        title_label = tk.Label(root, text="YouTube Video Downloader", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=15)
        
        # URL input frame
        url_frame = tk.Frame(root)
        url_frame.pack(pady=10, padx=20, fill="x")
        
        url_label = tk.Label(url_frame, text="YouTube URL:", font=("Arial", 10))
        url_label.pack(anchor="w")
        
        url_entry_frame = tk.Frame(url_frame)
        url_entry_frame.pack(fill="x", pady=5)
        
        self.url_entry = tk.Entry(url_entry_frame, font=("Arial", 10))
        self.url_entry.pack(side="left", fill="x", expand=True)
        
        self.fetch_btn = tk.Button(url_entry_frame, text="Fetch Resolutions", 
                                   command=self.fetch_formats,
                                   font=("Arial", 9, "bold"),
                                   bg="#2196F3", fg="white",
                                   cursor="hand2")
        self.fetch_btn.pack(side="left", padx=5)
        
        # Resolution selection frame
        resolution_frame = tk.Frame(root)
        resolution_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        resolution_label = tk.Label(resolution_frame, text="Available Resolutions:", 
                                    font=("Arial", 10))
        resolution_label.pack(anchor="w")
        
        # Listbox with scrollbar
        listbox_frame = tk.Frame(resolution_frame)
        listbox_frame.pack(fill="both", expand=True, pady=5)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.resolution_listbox = tk.Listbox(listbox_frame, font=("Courier", 9),
                                            yscrollcommand=scrollbar.set,
                                            height=8)
        self.resolution_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.resolution_listbox.yview)
        
        # Download path frame
        path_frame = tk.Frame(root)
        path_frame.pack(pady=10, padx=20, fill="x")
        
        path_label = tk.Label(path_frame, text="Download Location:", font=("Arial", 10))
        path_label.pack(anchor="w")
        
        path_entry_frame = tk.Frame(path_frame)
        path_entry_frame.pack(fill="x", pady=5)
        
        self.path_entry = tk.Entry(path_entry_frame, font=("Arial", 9))
        self.path_entry.insert(0, self.download_path)
        self.path_entry.pack(side="left", fill="x", expand=True)
        
        browse_btn = tk.Button(path_entry_frame, text="Browse", 
                              command=self.browse_folder, width=8)
        browse_btn.pack(side="left", padx=5)
        
        # Download button
        self.download_btn = tk.Button(root, text="Download Selected", 
                                     command=self.start_download,
                                     font=("Arial", 12, "bold"),
                                     bg="#4CAF50", fg="white",
                                     width=20, height=2,
                                     cursor="hand2",
                                     state="disabled")
        self.download_btn.pack(pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(root, length=500, mode='indeterminate')
        self.progress.pack(pady=5)
        
        # Status label
        self.status_label = tk.Label(root, text="Enter a YouTube URL and click 'Fetch Resolutions'", 
                                    font=("Arial", 9), fg="gray")
        self.status_label.pack(pady=5)
    
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)
            self.download_path = folder
    
    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        
        # Start fetching in separate thread
        thread = threading.Thread(target=self.get_video_formats, args=(url,))
        thread.start()
    
    def get_video_formats(self, url):
        try:
            self.fetch_btn.config(state="disabled")
            self.progress.start()
            self.status_label.config(text="Fetching available formats...", fg="blue")
            self.resolution_listbox.delete(0, tk.END)
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.video_info = ydl.extract_info(url, download=False)
            
            # Parse formats
            formats = self.video_info.get('formats', [])
            
            # Filter and organize formats
            video_formats = []
            for f in formats:
                # Only include formats with video
                if f.get('vcodec') != 'none' and f.get('height'):
                    resolution = f.get('height')
                    ext = f.get('ext', 'mp4')
                    fps = f.get('fps', 30)
                    filesize = f.get('filesize', 0)
                    has_audio = f.get('acodec') != 'none'
                    format_id = f.get('format_id')
                    
                    # Format size display
                    size_str = ""
                    if filesize:
                        size_mb = filesize / (1024 * 1024)
                        size_str = f"{size_mb:.1f}MB"
                    else:
                        size_str = "Size N/A"
                    
                    audio_str = "with audio" if has_audio else "video only"
                    
                    display_text = f"{resolution}p  {ext}  {fps}fps  {size_str}  ({audio_str})"
                    
                    video_formats.append({
                        'display': display_text,
                        'format_id': format_id,
                        'resolution': resolution,
                        'has_audio': has_audio
                    })
            
            # Sort by resolution (highest first)
            video_formats.sort(key=lambda x: x['resolution'], reverse=True)
            
            # Remove duplicates with same resolution and audio status
            seen = set()
            unique_formats = []
            for fmt in video_formats:
                key = (fmt['resolution'], fmt['has_audio'])
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(fmt)
            
            self.available_formats = unique_formats
            
            # Populate listbox
            for fmt in unique_formats:
                self.resolution_listbox.insert(tk.END, fmt['display'])
            
            self.progress.stop()
            self.status_label.config(text=f"✓ Found {len(unique_formats)} formats. Select one to download.", fg="green")
            self.download_btn.config(state="normal")
            
        except Exception as e:
            self.progress.stop()
            self.status_label.config(text="✗ Failed to fetch formats", fg="red")
            messagebox.showerror("Error", f"Failed to fetch formats:\n{str(e)}")
        finally:
            self.fetch_btn.config(state="normal")
    
    def start_download(self):
        selection = self.resolution_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a resolution from the list")
            return
        
        selected_index = selection[0]
        selected_format = self.available_formats[selected_index]
        
        self.download_path = self.path_entry.get().strip()
        if not os.path.exists(self.download_path):
            messagebox.showerror("Error", "Download path does not exist")
            return
        
        # Start download in separate thread
        thread = threading.Thread(target=self.download_video, args=(selected_format,))
        thread.start()
    
    def download_video(self, selected_format):
        try:
            # Disable button and start progress bar
            self.download_btn.config(state="disabled")
            self.fetch_btn.config(state="disabled")
            self.progress.start()
            self.status_label.config(text="Downloading...", fg="blue")
            
            format_id = selected_format['format_id']
            
            # Check if ffmpeg is available
            ffmpeg_available = self.check_ffmpeg()
            
            # If format has no audio
            if not selected_format['has_audio']:
                if ffmpeg_available:
                    # Merge with audio if ffmpeg is available
                    format_string = f"{format_id}+bestaudio[ext=m4a]/best"
                    merge_output = 'mp4'
                else:
                    # Download video-only without audio if ffmpeg not available
                    response = messagebox.askyesno(
                        "No Audio Warning",
                        "FFmpeg is not installed. This video will be downloaded WITHOUT AUDIO.\n\n"
                        "Do you want to continue?\n\n"
                        "To get audio, either:\n"
                        "• Install FFmpeg (see console for instructions)\n"
                        "• Select a format that says 'with audio'"
                    )
                    if not response:
                        self.progress.stop()
                        self.status_label.config(text="Download cancelled", fg="gray")
                        return
                    format_string = format_id
                    merge_output = None
            else:
                format_string = format_id
                merge_output = None
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            }
            
            if merge_output:
                ydl_opts['merge_output_format'] = merge_output
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video_info['webpage_url']])
            
            video_title = self.video_info.get('title', 'video')
            
            # Success
            self.progress.stop()
            audio_note = " (no audio)" if not selected_format['has_audio'] and not ffmpeg_available else ""
            self.status_label.config(text=f"✓ Downloaded: {video_title}{audio_note}", fg="green")
            messagebox.showinfo("Success", f"Video downloaded successfully!{audio_note}\n\nSaved to: {self.download_path}")
            
        except Exception as e:
            self.progress.stop()
            self.status_label.config(text="✗ Download failed", fg="red")
            messagebox.showerror("Error", f"Download failed:\n{str(e)}")
        
        finally:
            # Re-enable buttons
            self.download_btn.config(state="normal")
            self.fetch_btn.config(state="normal")
    
    def check_ffmpeg(self):
        """Check if ffmpeg is available"""
        try:
            import subprocess
            subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, creationflags=0x08000000 if os.name == 'nt' else 0)
            return True
        except:
            return False


def main():
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()


if __name__ == "__main__":
    main()