import json
import os
import requests

CONFIG_FILE = "config.json"

def load_config():
    """Carica le credenziali da config.json, se esiste."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"client_id": "", "client_secret": ""}

def save_config(client_id, client_secret):
    """Salva le credenziali in config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump({"client_id": client_id, "client_secret": client_secret}, f, indent=4)

def get_twitch_token():
    """Ottiene un token di accesso da Twitch usando le credenziali salvate."""
    config = load_config()
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")

    if not client_id or not client_secret:
        raise ValueError("Twitch Client ID e Client Secret non sono configurati!")

    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    return response.json().get("access_token")

