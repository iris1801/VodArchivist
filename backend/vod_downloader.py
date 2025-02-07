# backend/vod_downloader.py
import os
import yt_dlp
import queue
import threading
import time
import json
from datetime import datetime
from backend.database import SessionLocal
from backend.models import Download

# Directory di download
DOWNLOAD_PATH = "downloads"

# Coda per i download e stato dei download (dizionario)
download_queue = queue.Queue()
download_status = {}

# Flag globali per il controllo dei download
paused = False      # Quando True, il worker non processa nuovi job
stop_all = False    # Quando True, il worker salta il processing (vengono ignorati i job)
resume_event = threading.Event()
resume_event.set()  # Inizialmente, non è in pausa

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)


def get_next_episode_number(creator_name, year):
    """ Trova il prossimo numero episodio disponibile per il creator in base all'anno """
    season_path = os.path.join(DOWNLOAD_PATH, creator_name, f"Stagione {year}")
    if not os.path.exists(season_path):
        return 1  # Primo episodio della stagione

    episode_numbers = []
    for file in os.listdir(season_path):
        if file.endswith(".mp4"):
            parts = file.split(" - ")
            if len(parts) > 1 and "S" in parts[0] and "E" in parts[0]:
                try:
                    episode_number = int(parts[0].split("E")[1])
                    episode_numbers.append(episode_number)
                except ValueError:
                    continue

    return max(episode_numbers, default=0) + 1  # Prossimo episodio disponibile


def create_nfo_file(nfo_path, creator_name, title, year, episode_number, vod_url, aired_date):
    """ Crea un file .nfo per Plex nel formato corretto """
    nfo_content = f"""<episodedetails>
    <title>{title}</title>
    <originaltitle>{title}</originaltitle>
    <showtitle>{creator_name}</showtitle>
    <season>{year}</season>
    <episode>{episode_number}</episode>
    <plot>None</plot>
    <aired>{aired_date}</aired>
    <studio>Twitch</studio>
    <id>{vod_url}</id>
</episodedetails>"""

    with open(nfo_path, "w", encoding="utf-8") as nfo_file:
        nfo_file.write(nfo_content)


def download_vod(vod_url: str, quality: str = "best", progress_callback=None):
    """ Scarica un VOD e lo organizza nella cartella del creator e stagione """

    # Ottieni le informazioni sul video prima del download
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(vod_url, download=False)

    creator_name = info.get("uploader", "Unknown").replace(" ", "_")
    title = info.get("title", "Unknown").replace("/", "-")  # Evita slash nei nomi
    upload_date = info.get("upload_date", "Unknown")
    vod_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}" if upload_date.isdigit() else "Unknown"
    
    year = datetime.utcnow().year
    season_folder = f"Stagione {year}"

    # Trova il prossimo numero di episodio disponibile
    episode_number = get_next_episode_number(creator_name, year)
    episode_filename = f"{creator_name} - S{year}E{episode_number:02d} - {title}"

    # Creazione delle directory
    creator_path = os.path.join(DOWNLOAD_PATH, creator_name)
    season_path = os.path.join(creator_path, season_folder)
    os.makedirs(season_path, exist_ok=True)

    # Percorsi file
    video_path = os.path.join(season_path, f"{episode_filename}.mp4")
    nfo_path = os.path.join(season_path, f"{episode_filename}.nfo")

    options = {
        "outtmpl": video_path,
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    if progress_callback:
        options["progress_hooks"] = [progress_callback]

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(vod_url, download=True)

    # Crea il file NFO dopo il download
    create_nfo_file(nfo_path, creator_name, title, year, episode_number, vod_url, vod_date)

    return info


def download_worker():
    while True:
        # Blocca il worker se in pausa
        resume_event.wait()

        # Se è stato richiesto lo stop, svuota la coda e non processa job
        if stop_all:
            try:
                while True:
                    _ = download_queue.get_nowait()
                    download_queue.task_done()
            except queue.Empty:
                pass
            continue

        try:
            # Recupera il prossimo job con timeout (per poter controllare periodicamente stop/pausa)
            vod_url, quality = download_queue.get(timeout=1)
        except queue.Empty:
            continue

        # Se, dopo aver preso un job, è stato richiesto lo stop, salta il job
        if stop_all:
            download_queue.task_done()
            continue

        # Inizializza lo stato per questo download
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

        # Crea il record nel database
        db = SessionLocal()
        download_record = Download(vod_url=vod_url, quality=quality, status="In corso")
        db.add(download_record)
        db.commit()
        db.refresh(download_record)

        # Funzione di progress hook per aggiornare lo stato in tempo reale
        def progress_hook(d):
            if d.get('status') == 'downloading':
                download_status[vod_url]['progress'] = d.get('_percent_str', "N/A")
                download_status[vod_url]['speed'] = d.get('_speed_str', "N/A")
                download_status[vod_url]['eta'] = d.get('eta', "N/A")

        try:
            # Avvia il download
            info = download_vod(vod_url, quality=quality, progress_callback=progress_hook)
            channel_name = info.get("uploader", "Unknown")
            video_title = info.get("title", "Unknown")
            download_status[vod_url]['state'] = "Completato"
            download_status[vod_url]['channel'] = channel_name
            download_status[vod_url]['video_title'] = video_title

            # Aggiorna il record DB
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

