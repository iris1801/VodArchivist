import requests
from backend.config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, TWITCH_TOKEN_URL

def get_twitch_token():
    """Ottiene un access token per l'API di Twitch"""
    payload = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(TWITCH_TOKEN_URL, data=payload)
    
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        raise Exception(f"Errore nella richiesta del token: {response.text}")

