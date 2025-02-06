# backend/main.py
from fastapi import FastAPI
from .twitch_auth import get_twitch_token
from .twitch_api import get_vods
from pydantic import BaseModel
from .vod_downloader import download_queue, download_status
from .database import engine, Base
from .models import Download
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from .watchdog import start_watchdog, add_channel, list_channels

app = FastAPI()

# Avvia il watchdog
start_watchdog()

# Monta la cartella 'frontend' su un path (es. /dashboard)
app.mount("/dashboard", StaticFiles(directory="frontend", html=True), name="dashboard")

# Crea le tabelle nel database (se non esistono)
Base.metadata.create_all(bind=engine)

# Modelli per i request body
class VodRequest(BaseModel):
    vod_url: str
    quality: str = "best"

class WatchdogRequest(BaseModel):
    channel: str
    interval: int  # in secondi
    quality: str = "best"

@app.get("/")
def read_root():
    return {"message": "VodArchivist API is running!"}

@app.get("/auth/twitch")
def auth_twitch():
    token = get_twitch_token()
    return {"access_token": token}

@app.get("/vods/{channel_name}")
def fetch_vods(channel_name: str):
    try:
        vods = get_vods(channel_name)
        return {"channel": channel_name, "vods": vods}
    except Exception as e:
        return {"error": str(e)}

@app.post("/watchdog/")
def add_watchdog(request: WatchdogRequest):
    add_channel(request.channel, request.interval, request.quality)
    return {"message": f"Canale {request.channel} aggiunto al watchdog con intervallo {request.interval} secondi e qualità {request.quality}."}


@app.get("/watchdog/")
def get_watchdog_channels():
    """Restituisce la lista dei canali monitorati dal watchdog."""
    return list_channels()

@app.post("/download_vod/")
def queue_download_vod(request: VodRequest):
    download_queue.put((request.vod_url, request.quality))
    return {"message": f"Download accodato per {request.vod_url} con qualità {request.quality}p"}

@app.get("/download_status/")
def get_download_status():
    return download_status

@app.get("/channel/{channel_name}")
def get_channel_vods(channel_name: str):
    try:
        vods = get_vods(channel_name)
        return {"channel": channel_name, "vods": vods}
    except Exception as e:
        return {"error": str(e)}

@app.get("/downloads/")
def get_downloads():
    from .database import SessionLocal
    db = SessionLocal()
    downloads = db.query(Download).all()
    result = [
        {
            "vod_url": d.vod_url,
            "quality": d.quality,
            "status": d.status,
            "channel_name": d.channel_name,
            "video_title": d.video_title,
            "created_at": d.created_at.isoformat()
        }
        for d in downloads
    ]
    db.close()
    return result

# Endpoints per il controllo dei download
@app.post("/pause_downloads/")
def pause_downloads():
    from . import vod_downloader
    vod_downloader.paused = True
    vod_downloader.resume_event.clear()
    return {"message": "Download in pausa."}

@app.post("/resume_downloads/")
def resume_downloads():
    from . import vod_downloader
    vod_downloader.paused = False
    vod_downloader.resume_event.set()
    return {"message": "Download ripresi."}

@app.post("/stop_downloads/")
def stop_downloads():
    from . import vod_downloader
    vod_downloader.stop_all = True
    # Svuota la coda
    while not vod_downloader.download_queue.empty():
        try:
            vod_downloader.download_queue.get_nowait()
            vod_downloader.download_queue.task_done()
        except:
            break
    # Assicura che il worker non sia in pausa per poter gestire lo stop
    vod_downloader.resume_event.set()
    return {"message": "Tutti i download fermati."}

@app.post("/restart_downloads/")
def restart_downloads():
    from . import vod_downloader
    vod_downloader.stop_all = False
    vod_downloader.resume_event.set()
    return {"message": "Download riavviati."}

