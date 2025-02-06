import os
import yt_dlp

DOWNLOAD_PATH = "downloads"

def download_vod(vod_url: str, filename: str = None, quality: str = "best"):
    """Scarica un VOD di Twitch con la qualità desiderata"""
    if not os.path.exists(DOWNLOAD_PATH):
        os.makedirs(DOWNLOAD_PATH)
    
    options = {
        "outtmpl": f"{DOWNLOAD_PATH}/{filename}.mp4" if filename else f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([vod_url])

