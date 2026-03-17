from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

class ConsentVideo(Document):
    session_id: str
    user_id: str
    video_url: str
    video_public_id: str
    checksum: str
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "consent_videos"
