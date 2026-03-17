from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

class SessionParticipant(Document):
    session_id: str
    user_id: str
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None

    class Settings:
        name = "session_participants"
