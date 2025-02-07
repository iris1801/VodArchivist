# backend/vod_downloader.py
import os
import yt_dlp
import queue
import threading
import time
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


def generate_nfo(video_info, file_path):
    """ Crea un file .nfo accanto al video scaricato """
    nfo_content = f"""<video>
    <title>{video_info.get("title", "Unknown Video")}</title>
    <originaltitle>{video_info.get("title", "Unknown Video")}</originaltitle>
    <showtitle>{video_info.get("uploader", "Unknown Creator")}</showtitle>
    <season>{datetime.utcnow().year}</season>
    <plot>{video_info.get("description", "Nessuna descrizione disponibile.")}</plot>
    <aired>{video_info.get("upload_date", "Unknown Date")}</aired>
    <studio>{video_info.get("uploader", "Unknown Creator")}</studio>
    <id>{video_info.get("webpage_url", "N/A")}</id>
</video>"""

    # Scrive il file .nfo accanto al video
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(nfo_content)


def download_vod(vod_url: str, quality: str = "best", progress_callback=None):
    """ Scarica un VOD e lo organizza nella cartella del creator e stagione """

    # Ottieni le informazioni sul video prima del download
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(vod_url, download=False)

    creator_name = info.get("uploader", "Unknown").replace(" ", "_")
    year = datetime.utcnow().year
    season_folder = f"Season {year}"

    # Creazione delle directory
    creator_path = os.path.join(DOWNLOAD_PATH, creator_name)
    season_path = os.path.join(creator_path, season_folder)
    os.makedirs(season_path, exist_ok=True)

    # Definisce il percorso di output
    output_template = os.path.join(season_path, "%(title)s.%(ext)s")

    options = {
        "outtmpl": output_template,
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    if progress_callback:
        options["progress_hooks"] = [progress_callback]

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(vod_url, download=True)

    # Percorso del file video scaricato
    video_file_path = os.path.join(season_path, f"{info.get('title', 'Unknown')}.{info.get('ext', 'mp4')}")
    
    # Genera il file .nfo accanto al video
    nfo_file_path = os.path.splitext(video_file_path)[0] + ".nfo"
    generate_nfo(info, nfo_file_path)

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

