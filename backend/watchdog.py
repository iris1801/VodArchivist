# backend/watchdog.py
import os
import json
import time
import threading
from datetime import datetime
from backend.twitch_api import get_vods
from backend.vod_downloader import download_queue
from backend.database import SessionLocal

# Percorso del file per salvare i watchdog configurati
WATCHDOG_CONFIG_FILE = "backend/watchdog_config.json"

# Dizionario per tenere traccia dei canali monitorati
watched_channels = {}

def save_watchdog_config():
    """Salva i watchdog configurati su file JSON."""
    with open(WATCHDOG_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(watched_channels, f, indent=4, default=str)

def load_watchdog_config():
    """Carica i watchdog configurati dal file JSON."""
    global watched_channels
    if os.path.exists(WATCHDOG_CONFIG_FILE):
        with open(WATCHDOG_CONFIG_FILE, "r", encoding="utf-8") as f:
            watched_channels = json.load(f)
        # Converti i timestamp salvati in `datetime`
        for channel, data in watched_channels.items():
            data["last_checked"] = datetime.fromisoformat(data["last_checked"])

def watchdog_worker():
    """Controlla periodicamente se è scaduto l'intervallo per ciascun canale."""
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
                            download_queue.put((vod_url, data.get("quality", "best")))
                    db.close()
                    save_watchdog_config()  # Salva i dati aggiornati
                except Exception as e:
                    print(f"[Watchdog] Errore nel controllo per il canale {channel}: {str(e)}")
        time.sleep(5)

def start_watchdog():
    """Avvia il watchdog e carica la configurazione salvata."""
    load_watchdog_config()
    thread = threading.Thread(target=watchdog_worker, daemon=True)
    thread.start()

def add_channel(channel_name: str, interval: int, quality: str = "best"):
    """Aggiunge un nuovo canale al watchdog e salva la configurazione."""
    watched_channels[channel_name] = {
        "interval": interval,
        "quality": quality,
        "last_checked": datetime.utcnow().isoformat()
    }
    save_watchdog_config()

def list_channels():
    """Restituisce i canali attualmente monitorati."""
    return watched_channels
