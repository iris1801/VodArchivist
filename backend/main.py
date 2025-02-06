from fastapi import FastAPI
from backend.twitch_auth import get_twitch_token
from backend.twitch_api import get_vods
from pydantic import BaseModel
from backend.vod_downloader import download_vod

app = FastAPI()

# Modello per il request body
class VodRequest(BaseModel):
    vod_url: str
    quality: str = "best"

@app.get("/")
def read_root():
    return {"message": "VodArchivist API is running!"}

@app.get("/auth/twitch")
def auth_twitch():
    """Restituisce il token di autenticazione Twitch"""
    token = get_twitch_token()
    return {"access_token": token}

@app.get("/vods/{channel_name}")
def fetch_vods(channel_name: str):
    """Restituisce la lista dei VOD di un canale"""
    try:
        vods = get_vods(channel_name)
        return {"channel": channel_name, "vods": vods}
    except Exception as e:
        return {"error": str(e)}

@app.post("/download_vod/")
def fetch_and_download_vod(request: VodRequest):
    """Scarica un VOD da Twitch"""
    try:
        download_vod(request.vod_url, quality=request.quality)
        return {"message": f"Download avviato per {request.vod_url} con qualità {request.quality}p"}
    except Exception as e:
        return {"error": str(e)}
