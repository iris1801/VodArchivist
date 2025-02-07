# backend/vod_downloader.py
import os
import yt_dlp
import queue
import threading
import time
from datetime import datetime
from backend.database import SessionLocal
from backend.models import Download

# Directory principale di download
DOWNLOAD_PATH = "downloads"

# Coda per i download e stato dei download (dizionario)
download_queue = queue.Queue()
download_status = {}

# Flag globali per il controllo dei download
paused = False
stop_all = False
resume_event = threading.Event()
resume_event.set()  # Inizialmente non in pausa

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)


def generate_nfo(creator, title, season, episode, vod_url, published_date):
    """ Crea un file NFO per Plex con le informazioni del VOD. """
    nfo_content = f"""<episodedetails>
    <title>{title}</title>
    <originaltitle>{title}</originaltitle>
    <showtitle>{creator}</showtitle>
    <season>{season}</season>
    <episode>{episode}</episode>
    <plot>None</plot>
    <aired>{published_date}</aired>
    <studio>Twitch</studio>
    <id>{vod_url}</id>
</episodedetails>"""

    return nfo_content


def download_vod(vod_url: str, quality: str = "best", progress_callback=None):
    """ Scarica un VOD e lo organizza in cartelle dedicate """
    
    # Recupera informazioni sul video senza scaricare
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(vod_url, download=False)

    creator_name = info.get("uploader", "Unknown").replace(" ", "_")
    title = info.get("title", "Unknown").replace("/", "-")  # Evita caratteri non validi
    published_date = datetime.utcfromtimestamp(info.get("timestamp", time.time())).strftime("%Y-%m-%d")
    year = datetime.utcnow().year
    season_folder = f"Stagione {year}"

    # Determina il numero dell'episodio (basato sulla quantità di file nella stagione)
    creator_path = os.path.join(DOWNLOAD_PATH, creator_name, season_folder)
    os.makedirs(creator_path, exist_ok=True)
    episode_number = len([d for d in os.listdir(creator_path) if os.path.isdir(os.path.join(creator_path, d))]) + 1

    # Nome della cartella del VOD
    vod_folder_name = f"{creator_name} - S{year}E{episode_number:02d} - {title}"
    vod_folder_path = os.path.join(creator_path, vod_folder_name)
    os.makedirs(vod_folder_path, exist_ok=True)

    # Nome file VOD e NFO
    file_name = f"{creator_name} - S{year}E{episode_number:02d} - {title}"
    vod_path = os.path.join(vod_folder_path, f"{file_name}.mp4")
    nfo_path = os.path.join(vod_folder_path, f"{file_name}.nfo")

    # Opzioni di yt-dlp
    options = {
        "outtmpl": vod_path,
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    if progress_callback:
        options["progress_hooks"] = [progress_callback]

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(vod_url, download=True)

    # Genera il file .nfo
    nfo_content = generate_nfo(creator_name, title, year, episode_number, vod_url, published_date)
    with open(nfo_path, "w", encoding="utf-8") as f:
        f.write(nfo_content)

    return info


def download_worker():
    while True:
        resume_event.wait()

        if stop_all:
            try:
                while True:
                    _ = download_queue.get_nowait()
                    download_queue.task_done()
            except queue.Empty:
                pass
            continue

        try:
            vod_url, quality = download_queue.get(timeout=1)
        except queue.Empty:
            continue

        if stop_all:
            download_queue.task_done()
            continue

        download_status[vod_url] = {
            "state": "In corso",
            "progress": "0%",
            "speed": "N/A",
            "eta": "N/A",
            "channel": None,
            "video_title": None,
            "started_at": datetime.utcnow().isoformat()
        }
        print(f"[Worker] Avvio download per {vod_url} a {quality}p")

        db = SessionLocal()
        download_record = Download(vod_url=vod_url, quality=quality, status="In corso")
        db.add(download_record)
        db.commit()
        db.refresh(download_record)

        def progress_hook(d):
            if d.get('status') == 'downloading':
                download_status[vod_url]['progress'] = d.get('_percent_str', "N/A")
                download_status[vod_url]['speed'] = d.get('_speed_str', "N/A")
                download_status[vod_url]['eta'] = d.get('eta', "N/A")

        try:
            info = download_vod(vod_url, quality=quality, progress_callback=progress_hook)
            channel_name = info.get("uploader", "Unknown")
            video_title = info.get("title", "Unknown")
            download_status[vod_url]['state'] = "Completato"
            download_status[vod_url]['channel'] = channel_name
            download_status[vod_url]['video_title'] = video_title

            download_record.status = "Completato"
            download_record.channel_name = channel_name
            download_record.video_title = video_title
            db.commit()
            print(f"[Worker] Download completato per {vod_url}")

            time.sleep(10)
            del download_status[vod_url]
        except Exception as e:
            download_status[vod_url]['state'] = f"Errore: {str(e)}"
            download_record.status = f"Errore: {str(e)}"
            db.commit()
            print(f"[Worker] Errore nel download per {vod_url}: {str(e)}")

        db.close()
        download_queue.task_done()


# Avvia il worker in un thread separato
threading.Thread(target=download_worker, daemon=True).start()
