# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime
from backend.database import Base
import datetime

class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    vod_url = Column(String, unique=True, index=True)
    quality = Column(String)
    status = Column(String)
    file_path = Column(String, nullable=True)
    channel_name = Column(String, nullable=True)   # Nuova colonna
    video_title = Column(String, nullable=True)      # Nuova colonna
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

