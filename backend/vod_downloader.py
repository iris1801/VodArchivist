# backend/vod_downloader.py
import os
import yt_dlp
import queue
import threading
from backend.database import SessionLocal
from backend.models import Download

DOWNLOAD_PATH = "downloads"
download_queue = queue.Queue()
download_status = {}  # Questa variabile continuerà a tenere lo stato in memoria per visualizzazioni immediate
running = True  # Controllo per fermare il thread (se necessario)

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

def download_vod(vod_url: str, filename: str = None, quality: str = "best"):
    options = {
        "outtmpl": f"{DOWNLOAD_PATH}/{filename}.mp4" if filename else f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([vod_url])

def download_worker():
    while True:
        vod_url, quality = download_queue.get()
        # Aggiorna lo stato in memoria
        download_status[vod_url] = "In corso"
        # Crea una sessione DB per questo job
        db = SessionLocal()
        # Crea un record nel database
        download_record = Download(vod_url=vod_url, quality=quality, status="In corso")
        db.add(download_record)
        db.commit()
        db.refresh(download_record)
        print(f"[Worker] Avvio download per {vod_url} a {quality}p")
        try:
            download_vod(vod_url, quality=quality)
            download_status[vod_url] = "Completato"
            download_record.status = "Completato"
            db.commit()
            print(f"[Worker] Download completato per {vod_url}")
        except Exception as e:
            download_status[vod_url] = f"Errore: {str(e)}"
            download_record.status = f"Errore: {str(e)}"
            db.commit()
            print(f"[Worker] Errore nel download per {vod_url}: {str(e)}")
        db.close()
        download_queue.task_done()

# Avvia il worker in un thread separato
threading.Thread(target=download_worker, daemon=True).start()

