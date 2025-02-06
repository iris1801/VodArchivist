import os
import yt_dlp
import queue
import threading
import time

DOWNLOAD_PATH = "downloads"

# Inizializziamo la coda e lo stato dei download qui
download_queue = queue.Queue()
download_status = {}  # Aggiungi questa riga per definire lo stato dei download
running = True  # Controllo per fermare il thread

# Crea la cartella se non esiste
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

def download_vod(vod_url: str, filename: str = None, quality: str = "best"):
    """Scarica un VOD di Twitch con la qualità desiderata"""
    options = {
        "outtmpl": f"{DOWNLOAD_PATH}/{filename}.mp4" if filename else f"{DOWNLOAD_PATH}/%(title)s.%(ext)s",
        "format": f"best[height<={quality}]" if quality.isdigit() else "best",
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([vod_url])

def download_worker():
    """Worker che processa i download accodati e aggiorna lo stato"""
    while True:
        vod_url, quality = download_queue.get()
        # Aggiorna lo stato: inizia il download
        download_status[vod_url] = "In corso"
        print(f"[Worker] Avvio download per {vod_url} a {quality}p")
        try:
            download_vod(vod_url, quality=quality)
            download_status[vod_url] = "Completato"
            print(f"[Worker] Download completato per {vod_url}")
        except Exception as e:
            download_status[vod_url] = f"Errore: {str(e)}"
            print(f"[Worker] Errore nel download per {vod_url}: {str(e)}")
        download_queue.task_done()

# Avvia il worker in un thread separato
threading.Thread(target=download_worker, daemon=True).start()

