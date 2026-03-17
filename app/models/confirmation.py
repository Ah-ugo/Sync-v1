from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

class Confirmation(Document):
    session_id: str
    user_id: str
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None

    class Settings:
        name = "confirmations"
