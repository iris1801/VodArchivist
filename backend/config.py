import os

# Twitch API credentials (prendili da Twitch Developer Console)
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "h8ltlszdogk0soxgpcgjbr0l8rccwv")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "exk933c3bfh5go7b3i55c38grz59up")

# URL API Twitch
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"

