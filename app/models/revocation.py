from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from enum import Enum

class RevocationReason(str, Enum):
    CHANGED_MIND = "changed_mind"
    UNCOMFORTABLE = "uncomfortable"
    EMERGENCY = "emergency"
    OTHER = "other"

class Revocation(Document):
    session_id: str
    user_id: str
    reason: RevocationReason = RevocationReason.OTHER
    note: Optional[str] = None
    revoked_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "revocations"
