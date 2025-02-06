# backend/vod_downloader.py
import os
import yt_dlp
import queue
import threading
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

def download_vod(vod_url: str, filename: str = None, quality: str = "best", progress_callback=None):
    options = {
        "outtmpl": f"{DOWNLOAD_PATH}/{filename}.mp4" if filename else f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    if progress_callback:
        options["progress_hooks"] = [progress_callback]
    with yt_dlp.YoutubeDL(options) as ydl:
        # Estrae le informazioni e avvia il download
        info = ydl.extract_info(vod_url, download=True)
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
        except Exception as e:
            download_status[vod_url]['state'] = f"Errore: {str(e)}"
            download_record.status = f"Errore: {str(e)}"
            db.commit()
            print(f"[Worker] Errore nel download per {vod_url}: {str(e)}")
        db.close()
        download_queue.task_done()

# Avvia il worker in un thread separato
threading.Thread(target=download_worker, daemon=True).start()

