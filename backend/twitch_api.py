import requests
import json
import os
from backend.twitch_auth import get_twitch_token

CONFIG_FILE = "config.json"

def load_config():
    """Carica client_id e client_secret da config.json"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            return config.get("client_id", ""), config.get("client_secret", "")
    return "", ""

TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET = load_config()

TWITCH_API_URL = "https://api.twitch.tv/helix"

def get_user_id(username: str) -> str:
    """Ottiene l'ID di un utente Twitch a partire dal suo username"""
    token = get_twitch_token()
    
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    
    params = {"login": username}
    response = requests.get(f"{TWITCH_API_URL}/users", headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]["id"]
        else:
            raise ValueError("Utente non trovato")
    else:
        raise Exception(f"Errore API Twitch: {response.text}")


def get_vods(username: str):
    """Recupera la lista dei VOD di un canale Twitch"""
    user_id = get_user_id(username)
    token = get_twitch_token()
    
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }
    
    params = {
        "user_id": user_id,
        "type": "archive",  # Prende solo i VOD (non clip o highlights)
        "first": 10  # Numero massimo di VOD da recuperare
    }
    
    response = requests.get(f"{TWITCH_API_URL}/videos", headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()["data"]
    else:
        raise Exception(f"Errore API Twitch: {response.text}")

