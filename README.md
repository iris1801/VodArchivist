
![vodarchivist](https://github.com/user-attachments/assets/d6e2b70b-b0c7-45c3-a7e4-1b22c267251f)


🎥 VodArchivist - Your Personal Twitch VOD Archiver 🚀

Do you love Twitch content but hate seeing VODs vanish into the void? Fear not! VodArchivist is here to automate, archive, and manage your favorite Twitch VODs with ease. Whether you want to download VODs on-demand, set up automatic monitoring, or just build your own Twitch VOD library, VodArchivist has got you covered!


---

⭐ Features

✅ Download Twitch VODs - Just paste a VOD URL, choose a quality (e.g., 720p), and start downloading!
✅ Monitor & Auto-Download - Set up a watchdog for your favorite streamers and let VodArchivist grab new VODs automatically.
✅ Real-Time Progress - Track active downloads with live progress, speed, and estimated time remaining.
✅ Beautiful Dashboard - A clean, Twitch-inspired UI with a sleek purple gradient.
✅ Pause, Resume & Stop Downloads - You’re in full control. Pause an ongoing download, resume it later, or stop everything if your SSD starts crying.
✅ Download History & File Size Tracking - See what you've archived, when, and how big those files are.
✅ Modify or Delete Watchdogs - Change intervals, tweak quality settings, or remove a streamer from your auto-download list with just a click.
✅ NFO generation and fully compatible with Plex/Jellyfin scrapers


---

📸 Screenshot

 


---

🚀 Installation

1. Clone the repository

```
git clone https://github.com/iris1801/VodArchivist.git
cd VodArchivist
```

2. Install dependencies

If you're using a virtual environment, activate it first:

```
python3 -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

Then install the required packages:

```
pip install -r requirements.txt
```

3. Run the app

```
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Now, open your browser and go to:
📍 http://127.0.0.1:8000/dashboard/

Enjoy your personal Twitch VOD archive! 🎉


---

🔧 Running as a Service (Linux)

Want VodArchivist to run 24/7 on your server? Set it up as a systemd service!

```
sudo nano /etc/systemd/system/vodarchivist.service
```

Paste this inside:

```
[Unit]
Description=VodArchivist Service
After=network.target

[Service]
User=your_user
Group=your_user
WorkingDirectory=/path/to/VodArchivist
ExecStart=/usr/bin/env uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```
sudo systemctl daemon-reload
sudo systemctl enable vodarchivist
sudo systemctl start vodarchivist
```

Boom! 🎇 Now it runs on startup!


---

🛠 API Endpoints

Want to integrate VodArchivist with something else? Here's a quick look at the available API endpoints:

```
POST /download_vod/ → Queue a new VOD for download

GET /download_status/ → Check active download progress

GET /downloads/ → Get the history of completed downloads

POST /watchdog/ → Add a new channel to the auto-download list

PUT /watchdog/ → Update an existing watchdog

DELETE /watchdog/{channel_name} → Remove a channel from the watchdog list

GET /channel/{channel_name} → List available VODs for a streamer

```
---

🎮 Contributing

Got an idea to improve VodArchivist? Found a bug? Open an issue or submit a pull request! Let's make this the best Twitch VOD tool together! 🎉


---

📜 License

VodArchivist is open-source and available under the MIT License. Feel free to fork, modify, and share!


---

🤝 Credits

Huge thanks to:

yt-dlp for making VOD downloads possible.

FastAPI for powering our backend.

Vue.js for keeping the frontend snappy.

Twitch streamers for giving us endless content to archive! 🎥



---

🚀 Enjoy your VOD collection, and never miss a moment again! 🎬


