# backend/watchdog.py
import time
import threading
from datetime import datetime
from backend.twitch_api import get_vods
from backend.vod_downloader import download_queue
from backend.database import SessionLocal

# Dizionario per tenere traccia dei canali monitorati.
# La struttura sarà: { "nome_canale": {"interval": secondi, "quality": "best", "last_checked": datetime } }
watched_channels = {}

def watchdog_worker():
    """
    Controlla periodicamente se è scaduto l'intervallo per ciascun canale in watched_channels
    e, in tal caso, verifica i nuovi VOD.
    """
    while True:
        now = datetime.utcnow()
        for channel, data in list(watched_channels.items()):
            last_checked = data.get("last_checked", now)
            interval = data["interval"]
            if (now - last_checked).total_seconds() >= interval:
                watched_channels[channel]["last_checked"] = now
                print(f"[Watchdog] Controllo nuovi VOD per il canale: {channel}")
                try:
                    vods = get_vods(channel)
                    db = SessionLocal()
                    from backend.models import Download  # Import locale per evitare cicli
                    for vod in vods:
                        vod_url = vod.get("url")
                        exists = db.query(Download).filter(Download.vod_url == vod_url).first()
                        if not exists:
                            print(f"[Watchdog] Nuovo VOD trovato: {vod_url}. Accodato per il download.")
                            # Usa la qualità specificata per il canale
                            download_queue.put((vod_url, data.get("quality", "best")))
                    db.close()
                except Exception as e:
                    print(f"[Watchdog] Errore nel controllo per il canale {channel}: {str(e)}")
        time.sleep(5)

def start_watchdog():
    thread = threading.Thread(target=watchdog_worker, daemon=True)
    thread.start()

def add_channel(channel_name: str, interval: int, quality: str = "best"):
    watched_channels[channel_name] = {"interval": interval, "quality": quality, "last_checked": datetime.utcnow()}

def list_channels():
    return watched_channels

