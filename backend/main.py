# backend/main.py
from fastapi import FastAPI
from backend.twitch_auth import get_twitch_token
from backend.twitch_api import get_vods
from pydantic import BaseModel
from backend.vod_downloader import download_queue, download_status
from backend.database import engine, Base
from backend.models import Download

app = FastAPI()

# Crea le tabelle nel database (se non esistono)
Base.metadata.create_all(bind=engine)

# Modello per il request body
class VodRequest(BaseModel):
    vod_url: str
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

@app.post("/download_vod/")
def queue_download_vod(request: VodRequest):
    download_queue.put((request.vod_url, request.quality))
    return {"message": f"Download accodato per {request.vod_url} con qualità {request.quality}p"}

@app.get("/download_status/")
def get_download_status():
    return download_status

@app.get("/downloads/")
def get_downloads():
    from backend.database import SessionLocal
    db = SessionLocal()
    downloads = db.query(Download).all()
    result = [
        {
            "vod_url": d.vod_url,
            "quality": d.quality,
            "status": d.status,
            "created_at": d.created_at.isoformat()
        }
        for d in downloads
    ]
    db.close()
    return result

